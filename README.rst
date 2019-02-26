Install
------------

1 install from pip

.. code-block:: console

    pip install pubmed2

2 install from source code

.. code-block:: console

    git clone https://github.com/suqingdong/pubmed2.git
    cd pubmed2
    python setup.py install

3 use it directly

.. code-block:: console

    git clone https://github.com/suqingdong/pubmed2.git
    cd pubmed2/pubmed2
    python pubmed.py -h


Usage
------------

.. code-block:: console

    python pubmed.py 'ngs AND association'
    python pubmed.py '(LVNC) AND (mutation OR variation)' -m 50 -mif 5