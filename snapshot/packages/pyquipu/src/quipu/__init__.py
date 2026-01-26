# This allows this package to coexist with other distribution packages
# that contribute to the 'quipu' namespace.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
