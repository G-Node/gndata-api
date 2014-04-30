=========================================================
Integrated platform and API for electrophysiological data
=========================================================

GNData is a data management platform for neurophysiological data. GNData 
provides a storage system based on a data representation that is suitable to 
organize data and metadata from any electrophysiological experiment, with a 
functionality exposed via a common application programming interface (API). 
The API implementation is based on the Representational State Transfer (REST) 
pattern, which enables data access integration in software applications and 
facilitates the development of tools that communicate with the service. Client 
libraries that interact with the API provide direct data access from computing 
environments like Matlab or Python, enabling integration of data management 
into the scientist's experimental or analysis routines.


Dependencies
============

Using the GNData requires some other python packages to be installed:

- django_ Django python web framework
- django-tastypie_ REST controller for django
- h5py_ HDF5 for Python



.. external references
.. _documentation: http://g-node.github.io/g-node-portal/
.. _neo: http://neuralensemble.org/neo/
.. _h5py: http://www.h5py.org/
.. _django: https://www.djangoproject.com/
.. _django-tastypie: https://django-tastypie.readthedocs.org/
.. _sphinx: http://sphinx-doc.org/
.. _setuptools: https://pypi.python.org/pypi/setuptools
