import imp
import os
import sys
if sys.version_info >= (3, 0):
    import configparser
    import urllib.request as urllib
else:
    import ConfigParser as configparser
    import urllib2 as urllib
import argparse
import tarfile
import re

ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_FILE_PATH = os.path.join(ROOT_PATH, 'virtualenv_util.cfg')
VIRTUALENV_UTIL_PACKAGE_NAME = 'fruit_orchard'
VIRTUALENV_UTIL_PACKAGE_FILE_EXTENSION = '.tar.gz'
VIRTUALENV_UTIL_MODULE_NAME = 'virtualenv_util.py'

def _check_for_existing_package(bootstrap_directory, virtualenv_util_version = None):
    virtualenv_util_path = None
    
    # Look for something that appears like a virtualenv_util package already in the
    # bootstrap directory.  We do not attempt to re-bootstrap (redownload the
    # virtualenv_util package) if one of the correct version already exists.
    for item in os.listdir(bootstrap_directory):
        possible_dir = os.path.join(bootstrap_directory, item, VIRTUALENV_UTIL_PACKAGE_NAME)

        if item.startswith(VIRTUALENV_UTIL_PACKAGE_NAME) and os.path.isdir(possible_dir):
            # Special case... if specific version was specified, make sure
            # it is the right version.
            if virtualenv_util_version is None or \
                    (virtualenv_util_version is not None and item.split('-')[-1] == virtualenv_util_version):
                virtualenv_util_path = possible_dir
                virtualenv_util_version = item.split('-')[-1]   
                
    return virtualenv_util_path, virtualenv_util_version                        

def _get_newest_package_version(pypi_server):
    virtualenv_util_url_dir = pypi_server + '/' + VIRTUALENV_UTIL_PACKAGE_NAME

    f_remote = urllib.urlopen(virtualenv_util_url_dir)
    index = f_remote.read()

    # Very simple regex parser that finds all hyperlinks in the index
    # HTML... this may break in some cases, but we want to keep it super 
    # simple in the bootstrap.               
    hyperlinks = re.findall('href="(.*?)"', str(index.lower()))

    # Get all hyperlinks that start with the virtualenv package name
    # and end with the package extension.
    versions = []
    for hyperlink in hyperlinks:
        if hyperlink.startswith(VIRTUALENV_UTIL_PACKAGE_NAME+'-') and hyperlink.endswith(VIRTUALENV_UTIL_PACKAGE_FILE_EXTENSION):
            version = hyperlink.split('-')[-1].replace(VIRTUALENV_UTIL_PACKAGE_FILE_EXTENSION, '')
            versions.append(version)

    # Sort the versions from lowest to highest.
    # NOTE: This simple sort will work for most versions we expect to
    # use in the virtualenv_util package.  This could be enhanced.  
    versions.sort()

    # Select the highest version.        
    virtualenv_util_version = versions[-1]

    return virtualenv_util_version   


def _download_package(pypi_server, virtualenv_util_version, bootstrap_directory):

    # Download the package source tar from the server.
    virtualenv_util_tar_filename = '{}-{}{}'.format(VIRTUALENV_UTIL_PACKAGE_NAME, virtualenv_util_version, VIRTUALENV_UTIL_PACKAGE_FILE_EXTENSION)
    virtualenv_util_url = '/'.join([pypi_server, VIRTUALENV_UTIL_PACKAGE_NAME, virtualenv_util_tar_filename])

    f_remote = urllib.urlopen(virtualenv_util_url)
    f_local = open(os.path.join(ROOT_PATH, virtualenv_util_tar_filename), 'wb')
    f_local.write(f_remote.read())
    f_local.close()
    f_remote.close()

    # Unpack the tarball to the current directory.
    tarf = tarfile.open(os.path.join(ROOT_PATH, virtualenv_util_tar_filename), 'r:gz')
    tarf.extractall(ROOT_PATH)
    tarf.close()

    # Remove the tarball from the current directory.
    try:
        os.unlink(os.path.join(ROOT_PATH, virtualenv_util_tar_filename))
    except:
        pass

    virtualenv_util_path = os.path.join(ROOT_PATH, '{}-{}'.format(VIRTUALENV_UTIL_PACKAGE_NAME, virtualenv_util_version), VIRTUALENV_UTIL_PACKAGE_NAME)
    
    return virtualenv_util_path


def _get_options(config_file_path=None, options_overrides={}):
    '''Parse the virtualenv_util config file, if present.
    Any settings in the options_override dictionary will override those given 
    in the config file or on the command line.'''
    
    if config_file_path is None and options_overrides.get('cfg_file', None):
        config_file_path = options_overrides['cfg_file'] 
    
    if config_file_path is not None:
        config = configparser.SafeConfigParser()
        config.read([config_file_path])
        config_file_global_settings = dict(config.items("global"))
    else:
        config_file_global_settings = {}   
    
    parser = argparse.ArgumentParser(description='Bootstrap script for virtualenv_util')
    parser.add_argument('--pypi_pull_server', default='http://pypi.python.org/simple')
    parser.add_argument('--virtualenv_util_version', default=None)
    parser.add_argument('--virtualenv_util_path', default=None)
    parser.add_argument('--bootstrap_dir', default=ROOT_PATH)
    parser.add_argument('--cfg_file', default=None)   
    
    parser.set_defaults(**config_file_global_settings)
    options, remaining_args = parser.parse_known_args(sys.argv[1:])
    sys.argv = [sys.argv[0]] + remaining_args
    
    for key in options_overrides:
        setattr(options, key, options_overrides[key]) 
    
    options.cfg_file = config_file_path               
        
    return options     

        
def _import_and_execute_package(virtualenv_util_path, **args):
    package_script = os.path.join(virtualenv_util_path, VIRTUALENV_UTIL_MODULE_NAME)

    virtualenv_util = imp.load_source(VIRTUALENV_UTIL_PACKAGE_NAME, package_script)
    virtualenv_util.main(**args)                


def main(config_file_path=None, options_overrides={}, verbose=True):
    '''
    Execute the bootstrap script using the configuration file and/or    
    configuration options specified.  If necessary, will download the virtualenv 
    package from the server.  The package is then imported and the
    module entry point (main) function is called.
    '''

    options = _get_options(config_file_path, options_overrides)
    
    if options.virtualenv_util_path:

        virtualenv_util_path = os.path.normpath(options.virtualenv_util_path)

        if not os.path.isfile(os.path.join(virtualenv_util_path, VIRTUALENV_UTIL_MODULE_NAME)):
            raise RuntimeError
        else:
            if verbose:
                print('Using local {} package at {}...'.format(VIRTUALENV_UTIL_PACKAGE_NAME, virtualenv_util_path)) 
    else:
        virtualenv_util_path, version = _check_for_existing_package(options.bootstrap_dir, options.virtualenv_util_version)
        
        if virtualenv_util_path is not None:
            if verbose:
                print('Using previously downloaded {} package version {}...'.format(VIRTUALENV_UTIL_PACKAGE_NAME, version))

    # If we aren't using a previously downloaded or local version of the
    # package, try to download it. 
    if virtualenv_util_path is None:
        # Must have a pypi server specified... if not, we have no way of 
        # downloading the package. 
        pypi_server = options.pypi_pull_server
        if not pypi_server:
            raise RuntimeError('No PyPI server specified, cannot download {} package'.format(VIRTUALENV_UTIL_PACKAGE_NAME))

        if verbose:    
            print('Checking for {} package on server {}...'.format(VIRTUALENV_UTIL_PACKAGE_NAME, pypi_server))

        # If a specific version of the package hasn't been specified, get
        # the latest version on the download server.
        if options.virtualenv_util_version is None:
            version = _get_newest_package_version(pypi_server)     
        else:
            version = options.virtualenv_util_version    

        if verbose:    
            print('Downloading {} package version {}...'.format(VIRTUALENV_UTIL_PACKAGE_NAME, version))
        
        virtualenv_util_path = _download_package(pypi_server, version, options.bootstrap_dir) 

    if verbose:    
        print('Importing script: {}'.format(os.path.join(virtualenv_util_path, VIRTUALENV_UTIL_MODULE_NAME)))

    _import_and_execute_package(virtualenv_util_path, options_overrides=vars(options))  


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Bootstrap script for the virtualenv_util module (will attempt to download and execute the virtualenv_util main routine')

    parser.add_argument('--cfg_file', default=DEFAULT_CONFIG_FILE_PATH)   
    parsed, remaining_args = parser.parse_known_args(sys.argv[1:])
    sys.argv = [sys.argv[0]] + remaining_args       
        
    main(config_file_path = parsed.cfg_file)

    