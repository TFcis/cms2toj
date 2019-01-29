import os
import logging
import shutil


def makedirs(*path):
    path = os.path.join(*path)
    logging.debug("Checking exists {}".format(path))
    if not os.path.exists(path):
        logging.debug('Creating {}'.format(path))
        os.makedirs(path)


def copyfile(source, target):
    source = os.path.join(*source)
    target = os.path.join(*target)
    if not os.path.exists(target):
        logging.debug('Copying {} to {}'.format(source, target))
        shutil.copyfile(source, target)
