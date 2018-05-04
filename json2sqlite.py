#!/usr/bin/env python
# -*- coding=utf-8 -*-
import os
import json
import sqlite3


def connect_db(dbname):

    db = sqlite3.connect(dbname)
    cursor = db.cursor()

    return db, cursor


def create_table(dbname, tablename):

    sql = '''CREATE TABLE `{}` (
        journal varchar(50),
        factor varchar(10)
    );'''.format(tablename)

    db, cursor = connect_db(dbname)
    cursor.execute(sql)
    cursor.close()
    db.close()
    print 'successfully created new table: {}'.format(tablename)


def init_db(dbname, tablename):

    db, cursor = connect_db(dbname)

    sql = "SELECT COUNT(*) FROM sqlite_master where type='table' and name='{}'".format(tablename)
    cursor.execute(sql)
    result = cursor.fetchall()
    if result[0][0] != 0:
        print 'table already exists: {}'.format(tablename)
    else:
        create_table(dbname, tablename)

    cursor.close()
    db.close()

    db, cursor = connect_db(dbname)
    with open('impact_factor.json') as f:
        data = json.load(f)

    query = 'INSERT INTO `{}` VALUES (?, ?)'.format(tablename)
    for n, columns in enumerate(data.iteritems()):
        cursor.execute(query, columns)
        print '{} insert a row: {}'.format(n, columns)
    print 'database updated'

    sql = 'CREATE INDEX journal_factor_idx on {}(journal);'.format(tablename)
    cursor.execute(sql)
    print 'index updated'

    cursor.close()
    db.close()


def main():

    dbname = 'impact_factor.db'
    tablename = 'factor'

    if not os.path.exists(dbname):
        init_db(dbname, tablename)

    # Test
    db, cursor = connect_db(dbname)
    cursor.execute('select * from `{}` limit 5;'.format(tablename))
    print cursor.fetchall()
    cursor.execute("select * from `{}` where journal like '%{}%'".format(
        tablename, 'nature'))
    print cursor.fetchall()
    cursor.close()
    db.close()

if __name__ == "__main__":

    main()
