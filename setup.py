import numpy
from Cython.Build import cythonize
from setuptools import Extension, setup

setup(
    ext_modules=cythonize(
        [
            Extension(
                "haggregate.regularize",
                sources=["src/haggregate/regularize.pyx"],
                include_dirs=[numpy.get_include()],
            ),
            Extension(
                "rocc.calculation",
                sources=["src/rocc/calculation.pyx"],
                include_dirs=[numpy.get_include()],
            ),
        ]
    ),
)
