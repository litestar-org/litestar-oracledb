================
Litestar Asyncpg
================

Litestar Asyncpg is a plugin to make managing and creating database sessions easier for Litestar applications.

If you are using SQLAlchemy, you most likely want to use the SQLAlchemy Plugin.  However, if you are not using an ORM or need a simple tool to manage `oracledb` connections, this plugin is for you.

.. seealso:: It is built on:

    * `SQLAlchemy <https://www.sqlalchemy.org/>`_
    * `msgspec <https://jcristharif.com/msgspec/>`_
    * `Alembic <https://alembic.sqlalchemy.org/en/latest/>`_
    * `Typing Extensions <https://typing-extensions.readthedocs.io/en/latest/>`_

Installation
------------

Installing ``litestar-oracledb`` is as easy as calling your favorite Python package manager:

.. tab-set::

    .. tab-item:: pip
        :sync: key1

        .. code-block:: bash
            :caption: Using pip

            python3 -m pip install litestar-oracledb

    .. tab-item:: pdm

        .. code-block:: bash
            :caption: Using `PDM <https://pdm.fming.dev/>`_

            pdm add litestar-oracledb

    .. tab-item:: Poetry

        .. code-block:: bash
            :caption: Using `Poetry <https://python-poetry.org/>`_

            poetry add litestar-oracledb

Usage
-----

.. todo:: Add usage instructions

.. toctree::
    :titlesonly:
    :caption: Litestar Asyncpg Documentation
    :hidden:

    usage/index
    reference/index

.. toctree::
    :titlesonly:
    :caption: Development
    :hidden:

    changelog
    contribution-guide
