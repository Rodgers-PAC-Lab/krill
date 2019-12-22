"""Module that sets environment variables for local computers only (not heroku)

The two environment variables that are set are DATABASE_URL and
DJANGO_SECRET_KEY. The first sets up the connection to the database and
is set automatically in heroku environments. The second is extracted in
settings.py and used to set the variable SECRET_KEY there. By convention
I always use config:set to set DJANGO_SECRET_KEY.

The data can be read from a file 'local_cache' in the current directory,
or acquired from heroku using config:get. The values depend on which
git branch is currently active.

To run these actions, import this module and call:
    local_settings.set_environment_variables_if_not_on_heroku()

On Heroku's servers, these variables don't need to be set by this module,
because they are set by Heroku or by config:set. So, the function 
set_environment_variables_if_not_on_heroku checks for the presence of the
environment variable ON_HEROKU and does nothing if it is set. Even if
that variable were not set, this function would still do nothing, because
DJANGO_SECRET_KEY and DATABASE_URL are already set.

For "heroku local", this moduel does need to be run. And it will be run
because no environment variables (e.g., ON_HEROKU) are set in that case.

To generate the cache using config:get, call:
    local_settings.generate_local_cache()
"""
from __future__ import print_function
import os
import subprocess
import json

def run_cmd(cmd):
    """Runs a space separated command and returns the stripped output"""
    cwd = os.path.dirname(os.path.realpath(__file__))
    return subprocess.check_output(cmd.split(), cwd=cwd).strip()

def get_remote_name(branch_name):
    """Use the branch name to identify the corresponding remote name"""
    if branch_name == 'staging':
        remote_name = 'staging'
    elif branch_name == 'master':
        remote_name = 'heroku'
    else:
        # eg, HEAD in detached head state
        # typically we want to do that kind of stuff in staging
        # now that we're never using staging anymore, always assume master,
        # could be a feature branch
        print("warning: cannot interpret git branch %s, assuming heroku" % branch_name)
        remote_name = 'heroku'

    return remote_name

def get_branch_name():
    branch_name = run_cmd('git rev-parse --abbrev-ref HEAD')
    return branch_name

def set_environment_variables(verbose=False):
    """Set DATABASE_URL and DJANGO_SECRET_KEY environment variables.
    
    First we try to read these values from a local cache in the
    same directory as this file. If that fails, we use heroku config:get
    to get them from heroku.
    
    If the variables are already set, they will not be overwritten.
    """
    # Return immediately if the environment variables are already set
    current_du = os.environ.get('DATABASE_URL')
    current_sk = os.environ.get('DJANGO_SECRET_KEY')
    if current_du is not None and current_sk is not None:
        if verbose:
            print("[local_settings] environment variables already set, returning")
        return
    
    # Always run this in the directory of this file, rather than
    # wherever it's being imported
    cwd = os.path.dirname(os.path.realpath(__file__))
    
    # Get the remote name, to use with config:get or as a key into cache
    branch_name = get_branch_name()
    remote_name = get_remote_name(branch_name)
    if verbose:
        print("[local_settings] we are in branch %s and remote %s" % (
            branch_name, remote_name))
    
    ## Load from local cache if it exists, or otherwise use config:get
    local_cache_name = os.path.join(cwd, 'local_cache')
    if os.path.exists(local_cache_name):
        # Load the local cache
        with file(local_cache_name) as fi:
            data = json.load(fi)
        
        # Extract data just for this branch
        data = data[remote_name]

        if verbose:
            print("[local_settings] got information from cache")

    else:
        data = {
            'database_url': run_cmd(
                'heroku config:get DATABASE_URL --remote %s' % remote_name),
            'secret_key': run_cmd(
                'heroku config:get DJANGO_SECRET_KEY --remote %s' % remote_name),
        }

        if verbose:
            print("[local_settings] got information from config:get")

    ## Set the environment variables accordingly
    if os.environ.get('DATABASE_URL') is None:
        if verbose:
            print("[local_settings] set DATABASE_URL to %s..." % (
                data['database_url'][:18]))
        os.environ.setdefault('DATABASE_URL', data['database_url'])
    if os.environ.get('DJANGO_SECRET_KEY') is None:
        if verbose:
            print("[local_settings] set DJANGO_SECRET_KEY to %s ..." % (
                data['secret_key'][:5]))
        os.environ.setdefault('DJANGO_SECRET_KEY', data['secret_key'])

def generate_local_cache(force=False):
    """Use config:get to generate the file local_cache
    
    Tries to get the environment variables from both 'heroku' and 'staging'
    remotes. Issues warning if either of those remotes do not exist.
    Generates a JSON file called "local_cache" in the directory of this
    file with these values. This can be loaded by set_environment_variables.
    Will raise IOError if this file already exists unless force=True.
    
    The cache is a dict keyed by the remote name.
    """
    data = {}
    for remote_name in ['heroku', 'staging']:
        try:
            database_url = run_cmd(
                'heroku config:get DATABASE_URL --remote %s' % remote_name)
            secret_key = run_cmd(
                'heroku config:get DJANGO_SECRET_KEY --remote %s' % remote_name)
        except subprocess.CalledProcessError:
            print("could not run config:get on remote %s, excluding from cache" % remote_name)
            continue
        
        data[remote_name] = {
            'database_url': database_url,
            'secret_key': secret_key,
        }
    
    # Get the cache name and error if it would be overwritten
    cwd = os.path.dirname(os.path.realpath(__file__))
    local_cache_name = os.path.join(cwd, 'local_cache')
    if not force and os.path.exists(local_cache_name):
        raise IOError(
            "local cache already exists, delete %s" % local_cache_name)
    
    # Store
    with file(local_cache_name, 'w') as fi:
        json.dump(data, fi, indent=4)

def set_environment_variables_if_not_on_heroku():
    if os.environ.get('ON_HEROKU') is None:
        set_environment_variables()
