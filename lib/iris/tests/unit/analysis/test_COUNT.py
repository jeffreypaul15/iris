# (C) British Crown Copyright 2013 - 2018, Met Office
#
# This file is part of Iris.
#
# Iris is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Iris is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Iris.  If not, see <http://www.gnu.org/licenses/>.
"""Unit tests for the :data:`iris.analysis.COUNT` aggregator."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa

# Import iris.tests first so that some things can be initialised before
# importing anything else.
import iris.tests as tests

import numpy as np
import numpy.ma as ma

from iris.analysis import COUNT
from iris.cube import Cube
from iris.coords import DimCoord
from iris._lazy_data import as_lazy_data


class Test_basics(tests.IrisTest):
    def setUp(self):
        data = np.array([1, 2, 3, 4, 5])
        coord = DimCoord([6, 7, 8, 9, 10], long_name='foo')
        self.cube = Cube(data)
        self.cube.add_dim_coord(coord, 0)
        self.lazy_cube = Cube(as_lazy_data(data))
        self.lazy_cube.add_dim_coord(coord, 0)
        self.func = lambda x: x >= 3

    def test_name(self):
        self.assertEqual(COUNT.name(), 'count')

    def test_no_function(self):
        exp_emsg = "function must be a callable. Got <class 'NoneType'>"
        with self.assertRaisesRegexp(TypeError, exp_emsg):
            self.lazy_cube.collapsed("foo", COUNT)

    def test_not_callable(self):
        with self.assertRaisesRegexp(TypeError, 'function must be a callable'):
            self.cube.collapsed("foo", COUNT, function='wibble')

    def test_lazy_not_callable(self):
        with self.assertRaisesRegexp(TypeError, 'function must be a callable'):
            self.lazy_cube.collapsed("foo", COUNT, function='wibble')

    def test_collapse(self):
        cube = self.cube.collapsed("foo", COUNT, function=self.func)
        self.assertArrayEqual(cube.data, [3])

    def test_lazy(self):
        cube = self.lazy_cube.collapsed("foo", COUNT, function=self.func)
        self.assertTrue(cube.has_lazy_data())

    def test_lazy_collapse(self):
        cube = self.lazy_cube.collapsed("foo", COUNT, function=self.func)
        self.assertArrayEqual(cube.data, [3])


class Test_units_func(tests.IrisTest):
    def test(self):
        self.assertIsNotNone(COUNT.units_func)
        new_units = COUNT.units_func(None)
        self.assertEqual(new_units, 1)


class Test_masked(tests.IrisTest):
    def setUp(self):
        self.cube = Cube(ma.masked_equal([1, 2, 3, 4, 5], 3))
        self.cube.add_dim_coord(DimCoord([6, 7, 8, 9, 10], long_name='foo'), 0)
        self.func = lambda x: x >= 3

    def test_ma(self):
        cube = self.cube.collapsed("foo", COUNT, function=self.func)
        self.assertArrayEqual(cube.data, [2])


class Test_lazy(tests.IrisTest):
    def setUp(self):
        data = np.array([1, 2, 3, 4, 5])
        self.cube = Cube(as_lazy_data(data))
        self.cube.add_dim_coord(DimCoord([6, 7, 8, 9, 10], long_name='foo'), 0)
        self.func = lambda x: x >= 3

    def test_lazy_oper(self):
        cube = self.cube.collapsed("foo", COUNT, function=self.func)
        self.assertTrue(cube.has_lazy_data())

    def test_collapse(self):
        result = self.cube.collapsed("foo", COUNT, function=self.func)
        self.cube.data
        expected = self.cube.collapsed("foo", COUNT, function=self.func)
        self.assertArrayEqual(result.data, expected.data)


class Test_lazy_masked(tests.IrisTest):
    def setUp(self):
        lazy_data = as_lazy_data(ma.masked_equal([1, 2, 3, 4, 5], 3))
        self.lazy_cube = Cube(lazy_data)
        self.lazy_cube.add_dim_coord(DimCoord([6, 7, 8, 9, 10],
                                              long_name='foo'),
                                     0)
        self.func = lambda x: x >= 3

    def test_ma(self):
        cube = self.lazy_cube.collapsed("foo", COUNT, function=self.func)
        self.assertTrue(cube.has_lazy_data())
        self.assertArrayEqual(cube.data, [2])


class Test_aggregate_shape(tests.IrisTest):
    def test(self):
        shape = ()
        kwargs = dict()
        self.assertTupleEqual(COUNT.aggregate_shape(**kwargs), shape)
        kwargs = dict(wibble='wobble')
        self.assertTupleEqual(COUNT.aggregate_shape(**kwargs), shape)


if __name__ == "__main__":
    tests.main()
