.. CodeGra.de documentation master file, created by
   sphinx-quickstart on Thu Jun 29 15:43:19 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.
.. rst-class:: fa fa-fontawesome

Welcome to CodeGrade
======================================

.. include:: about/codegradefeatures.rst

The code of CodeGrade, the Filesystem and the numerous editor plugins is
open-source and available on `Github <https://github.com/CodeGra-de>`_. More
information on getting started with CodeGrade at your institute can be found on
`CodeGrade <https://codegra.de>`_.

The documentation of CodeGrade consists of a developer documentation and a user
documentation:


.. only:: not latex

    .. toctree::
        :maxdepth: 1
        :caption: About CodeGrade

        about/whatis
        about/changelog
        about/history
        about/authors
        about/technologies
        about/contributing
        about/contact

.. _user-docs:

.. toctree::
   :maxdepth: 2
   :caption: User Documentation

   user/quickstart.rst
   user/overview.rst
   user/codeviewer.rst
   user/management.rst
   user/plagiarism.rst
   user/groups.rst
   user/permissions.rst
   user/preferences.rst
   Filesystem <https://fs-docs.codegra.de>
   user/lms.rst


.. only:: latex

    .. toctree::
        :maxdepth: 1
        :caption: About CodeGrade

        about/whatis
        about/changelog
        about/history
        about/authors
        about/technologies
        about/contributing
        about/contact

.. only:: latex

    .. toctree::
        :maxdepth: 1
        :caption: Developer Documentation

        building
        running

.. only:: not latex

    .. toctree::
        :maxdepth: 1
        :caption: Developer Documentation

        building
        running
        api
        code
