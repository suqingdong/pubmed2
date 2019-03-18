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
    pubmed -h


Usage
------------

.. code-block:: console

    pubmed 'ngs AND association'
    pubmed '(LVNC) AND (mutation OR variation)' -m 50 -mif 5


FAQ
------------

*Install failed?*

- Windows maybe need `VCForPython <https://www.microsoft.com/en-us/download/details.aspx?id=44266>`_
- Linux maybe need ``python-dev`` or ``python-devel``
