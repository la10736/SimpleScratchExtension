__author__ = 'damico'
import logging


try:
    from unitest.mock import *
except ImportError:
    try:
        from mock import *
    except:
        logging.error("You must install mock package: try from your shell 'pip install mock'")
        raise
