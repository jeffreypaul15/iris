# (C) British Crown Copyright 2010 - 2016, Met Office
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
"""Integration tests for :mod:`iris.analysis.trajectory`."""

from __future__ import (absolute_import, division, print_function)
from six.moves import (filter, input, map, range, zip)  # noqa
import six

# import iris tests first so that some things can be initialised before
# importing anything else
import iris.tests as tests

import biggus
import numpy as np

import iris.analysis.trajectory
import iris.tests.stock


@tests.skip_data
class TestSimple(tests.IrisTest):
    def test_invalid_coord(self):
        cube = iris.tests.stock.realistic_4d()
        sample_pts = [('altitude', [0, 10, 50])]
        with self.assertRaises(ValueError):
            iris.analysis.trajectory.interpolate(cube, sample_pts, 'nearest')


class TestTrajectory(tests.IrisTest):
    def test_trajectory_definition(self):
        # basic 2-seg line along x
        waypoints = [{'lat': 0, 'lon': 0}, {'lat': 0, 'lon': 1},
                     {'lat': 0, 'lon': 2}]
        trajectory = iris.analysis.trajectory.Trajectory(waypoints,
                                                         sample_count=21)

        self.assertEqual(trajectory.length, 2.0)
        self.assertEqual(trajectory.sampled_points[19],
                         {'lat': 0.0, 'lon': 1.9000000000000001})

        # 4-seg m-shape
        waypoints = [{'lat': 0, 'lon': 0}, {'lat': 1, 'lon': 1},
                     {'lat': 0, 'lon': 2}, {'lat': 1, 'lon': 3},
                     {'lat': 0, 'lon': 4}]
        trajectory = iris.analysis.trajectory.Trajectory(waypoints,
                                                         sample_count=33)

        self.assertEqual(trajectory.length, 5.6568542494923806)
        self.assertEqual(trajectory.sampled_points[31],
                         {'lat': 0.12499999999999989, 'lon': 3.875})


@tests.skip_data
class TestColpex(tests.IrisTest):
    def setUp(self):
        # Load the COLPEX data => TZYX
        path = tests.get_data_path(['PP', 'COLPEX',
                                    'theta_and_orog_subset.pp'])
        cube = iris.load_cube(path, 'air_potential_temperature')
        cube.coord('grid_latitude').bounds = None
        cube.coord('grid_longitude').bounds = None
        # TODO: Workaround until regrid can handle factories
        cube.remove_aux_factory(cube.aux_factories[0])
        cube.remove_coord('surface_altitude')
        self.cube = cube

    def test_trajectory_extraction(self):
        # Pull out a single point - no interpolation required
        single_point = iris.analysis.trajectory.interpolate(
            self.cube, [('grid_latitude', [-0.1188]),
                        ('grid_longitude', [359.57958984])])
        expected = self.cube[..., 10, 0].data

        self.assertArrayAllClose(single_point[..., 0].data,
                                 expected, rtol=2.0e-7)
        self.assertCML(single_point, ('trajectory', 'single_point.cml'),
                       checksum=False)

    def test_trajectory_extraction_calc(self):
        # Pull out another point and test against a manually calculated result.
        single_point = [['grid_latitude', [-0.1188]],
                        ['grid_longitude', [359.584090412]]]
        scube = self.cube[0, 0, 10:11, 4:6]
        x0 = scube.coord('grid_longitude')[0].points
        x1 = scube.coord('grid_longitude')[1].points
        y0 = scube.data[0, 0]
        y1 = scube.data[0, 1]
        expected = y0 + ((y1 - y0) * ((359.584090412 - x0)/(x1 - x0)))
        trajectory_cube = iris.analysis.trajectory.interpolate(scube,
                                                               single_point)
        self.assertArrayAllClose(trajectory_cube.data, expected, rtol=2.0e-7)

    def _traj_to_sample_points(self, trajectory):
        sample_points = []
        src_points = trajectory.sampled_points
        for name in six.iterkeys(src_points[0]):
            values = [point[name] for point in src_points]
            sample_points.append((name, values))
        return sample_points

    def test_trajectory_extraction_axis_aligned(self):
        # Extract a simple, axis-aligned trajectory that is similar to an
        # indexing operation.
        # (It's not exactly the same because the source cube doesn't have
        # regular spacing.)
        waypoints = [
            {'grid_latitude': -0.1188, 'grid_longitude': 359.57958984},
            {'grid_latitude': -0.1188, 'grid_longitude': 359.66870117}
        ]
        trajectory = iris.analysis.trajectory.Trajectory(waypoints,
                                                         sample_count=100)

        sample_points = self._traj_to_sample_points(trajectory)
        trajectory_cube = iris.analysis.trajectory.interpolate(self.cube,
                                                               sample_points)
        self.assertCML(trajectory_cube, ('trajectory',
                                         'constant_latitude.cml'))

    def test_trajectory_extraction_zigzag(self):
        # Extract a zig-zag trajectory
        waypoints = [
            {'grid_latitude': -0.1188, 'grid_longitude': 359.5886},
            {'grid_latitude': -0.0828, 'grid_longitude': 359.6606},
            {'grid_latitude': -0.0468, 'grid_longitude': 359.6246},
        ]
        trajectory = iris.analysis.trajectory.Trajectory(waypoints,
                                                         sample_count=20)
        sample_points = self._traj_to_sample_points(trajectory)
        trajectory_cube = iris.analysis.trajectory.interpolate(
            self.cube[0, 0], sample_points)
        expected = np.array([287.95953369, 287.9190979, 287.95550537,
                             287.93240356, 287.83850098, 287.87869263,
                             287.90942383, 287.9463501, 287.74365234,
                             287.68856812, 287.75588989, 287.54611206,
                             287.48522949, 287.53356934, 287.60217285,
                             287.43795776, 287.59701538, 287.52468872,
                             287.45025635, 287.52716064], dtype=np.float32)

        self.assertCML(trajectory_cube, ('trajectory', 'zigzag.cml'),
                       checksum=False)
        self.assertArrayAllClose(trajectory_cube.data, expected, rtol=2.0e-7)


@tests.skip_data
class TestTriPolar(tests.IrisTest):
    def setUp(self):
        # load data
        cubes = iris.load(tests.get_data_path(['NetCDF', 'ORCA2',
                                               'votemper.nc']))
        cube = cubes[0]
        # The netCDF file has different data types for the points and
        # bounds of 'depth'. This wasn't previously supported, so we
        # emulate that old behaviour.
        b32 = cube.coord('depth').bounds.astype(np.float32)
        cube.coord('depth').bounds = b32
        self.cube = cube
        # define a latitude trajectory (put coords in a different order
        # to the cube, just to be awkward)
        latitudes = list(range(-90, 90, 2))
        longitudes = [-90]*len(latitudes)
        self.sample_points = [('longitude', longitudes),
                              ('latitude', latitudes)]

    def test_tri_polar(self):

        # extract
        sampled_cube = iris.analysis.trajectory.interpolate(self.cube,
                                                            self.sample_points)
        self.assertCML(sampled_cube, ('trajectory',
                                      'tri_polar_latitude_slice.cml'))

    def test_tri_polar_method_linear_fails(self):
        # Try to request linear interpolation.
        # Not allowed, as we have multi-dimensional coords.
        self.assertRaises(iris.exceptions.CoordinateMultiDimError,
                          iris.analysis.trajectory.interpolate, self.cube,
                          self.sample_points, method="linear")

    def test_tri_polar_method_unknown_fails(self):
        # Try to request unknown interpolation.
        self.assertRaises(ValueError, iris.analysis.trajectory.interpolate,
                          self.cube, self.sample_points, method="linekar")


class TestHybridHeight(tests.IrisTest):
    def test_hybrid_height(self):
        cube = tests.stock.simple_4d_with_hybrid_height()
        # Put a biggus array on the cube so we can test deferred loading.
        cube.lazy_data(biggus.NumpyArrayAdapter(cube.data))

        traj = (('grid_latitude', [20.5, 21.5, 22.5, 23.5]),
                ('grid_longitude', [31, 32, 33, 34]))
        xsec = iris.analysis.trajectory.interpolate(cube, traj,
                                                    method='nearest')

        # Check that creating the trajectory hasn't led to the original
        # data being loaded.
        self.assertTrue(cube.has_lazy_data())
        self.assertCML([cube, xsec], ('trajectory', 'hybrid_height.cml'))


if __name__ == '__main__':
    tests.main()