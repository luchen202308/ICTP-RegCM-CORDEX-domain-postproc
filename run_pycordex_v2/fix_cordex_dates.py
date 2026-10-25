#!/usr/bin/env python3

"""
Fix the time axis and the file names of CORDEX files written by pycordexer
versions older than 2026-10-23 (commit before the time handling fixes).

For each file:

- the time and time_bnds values are converted to days since 1950-01-01 and
  rounded to the nearest 30 minutes, removing the float32 rounding errors of
  the old versions;
- time bounds are added to time mean variables that lack them (prsn);
- the file is renamed to have the time range of its time axis ("yyyyMM",
  "yyyyMMdd" or "yyyyMMddhhmm"), or no time range for fx files.

Files whose data cannot be fixed this way (empty files and evspsblpot daily
and monthly values, which were thinned and not averaged) are only reported:
they must be reprocessed.

Without the --apply option nothing is modified, and the script only prints
what it would do.
"""

import argparse
import os
import re
import sys

import numpy as np
from netCDF4 import Dataset, num2date, date2num


__copyright__ = 'Copyright (C) 2026 ICTP'
__author__ = 'Graziano Giuliani <ggiulian@ictp.it>'


CORDEX_TIME_UNITS = 'days since 1950-01-01 00:00:00'
# All the times written by pycordexer are multiples of 30 minutes
TIME_RESOLUTION = 1.0 / 48.0
TIME_RANGE = re.compile(r'^\d{6,12}-\d{6,12}$')

# The step (in days) of each frequency, to build missing time bounds
FREQUENCY_STEP = {'1hr': 1.0 / 24.0, '3hr': 3.0 / 24.0, '6hr': 6.0 / 24.0,
                  'day': 1.0}
# Time mean variables saved without time bounds by the old versions
MISSING_BOUNDS = ('prsn',)


def to_cordex_days(values, units, calendar):
    """The time values in CORDEX units, without any rounding"""
    values = np.asarray(values, dtype=np.float64)
    if units == CORDEX_TIME_UNITS:
        return values
    dates = num2date(values.ravel(), units=units, calendar=calendar)
    return np.reshape(
        date2num(dates, units=CORDEX_TIME_UNITS, calendar=calendar),
        values.shape
    )


def snap(values):
    """Round the time values to the nearest 30 minutes"""
    return np.round(values / TIME_RESOLUTION) * TIME_RESOLUTION


def time_range(dates, frequency):
    if frequency == 'mon':
        fmt = '{0.year:04d}{0.month:02d}'
    elif frequency == 'day':
        fmt = '{0.year:04d}{0.month:02d}{0.day:02d}'
    else:
        fmt = '{0.year:04d}{0.month:02d}{0.day:02d}{0.hour:02d}{0.minute:02d}'
    return fmt.format(dates[0]) + '-' + fmt.format(dates[-1])


def fix_file(path, apply):
    """
    Returns a tuple (actions, problem, new_path): the list of the changes
    needed by the file, a string describing a problem that only reprocessing
    can fix (or None) and the new path of the file (or None if the name is
    already correct).
    """
    actions = []
    problem = None
    mode = 'a' if apply else 'r'
    with Dataset(path, mode) as nc:
        frequency = nc.getncattr('frequency')
        variable_id = nc.getncattr('variable_id')

        new_range = None
        if 'time' in nc.variables:
            time = nc.variables['time']
            if time.size == 0:
                return [], 'no time steps', None
            if variable_id == 'evspsblpot' and frequency in ('day', 'mon'):
                problem = 'daily values were thinned, not averaged'
            calendar = time.getncattr('calendar')
            units = time.getncattr('units')

            values = to_cordex_days(time[:], units, calendar)
            new_values = snap(values)
            if units != CORDEX_TIME_UNITS:
                actions.append('time units "{}" -> "{}"'.format(
                    units, CORDEX_TIME_UNITS))
            shift = np.max(np.abs(new_values - values))
            if shift > 1.0e-9:
                actions.append('time values corrected by up to {:.1f} '
                               'minutes'.format(shift * 1440.0))

            bounds_name = time.getncattr('bounds') \
                if 'bounds' in time.ncattrs() else None
            new_bounds = None
            if bounds_name is not None and bounds_name in nc.variables:
                bounds = to_cordex_days(nc.variables[bounds_name][:],
                                        units, calendar)
                new_bounds = snap(bounds)
                if np.any(np.abs(new_bounds - bounds) > 1.0e-9):
                    actions.append('time bounds corrected')
            elif (variable_id in MISSING_BOUNDS and
                  frequency in FREQUENCY_STEP):
                half = FREQUENCY_STEP[frequency] / 2.0
                new_bounds = np.stack((new_values - half,
                                       new_values + half), axis=-1)
                bounds_name = 'time_bnds'
                actions.append('time bounds added')

            if apply:
                time[:] = new_values
                time.setncattr('units', CORDEX_TIME_UNITS)
                if new_bounds is not None:
                    if bounds_name not in nc.variables:
                        if 'bnds' not in nc.dimensions:
                            nc.createDimension('bnds', 2)
                        nc.createVariable(bounds_name, 'f8',
                                          ('time', 'bnds'))
                        time.setncattr('bounds', bounds_name)
                    nc.variables[bounds_name][:] = new_bounds

            dates = num2date(new_values, units=CORDEX_TIME_UNITS,
                             calendar=calendar)
            new_range = time_range(dates, frequency)

    # The new file name
    directory, name = os.path.split(path)
    parts = name[:-3].split('_')
    if TIME_RANGE.match(parts[-1]):
        parts = parts[:-1]
    if new_range is not None:
        parts.append(new_range)
    new_name = '_'.join(parts) + '.nc'
    new_path = None
    if new_name != name:
        new_path = os.path.join(directory, new_name)
        actions.append('rename to {}'.format(new_name))
    return actions, problem, new_path


def find_files(paths):
    for path in paths:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in sorted(files):
                    if f.endswith('.nc'):
                        yield os.path.join(root, f)
        else:
            yield path


def main():
    parser = argparse.ArgumentParser(
        description='Fix the time axis and the names of CORDEX files written '
                    'by older pycordexer versions.'
    )
    parser.add_argument('paths', nargs='+',
                        help='CORDEX files or directories (searched '
                             'recursively for .nc files)')
    parser.add_argument('--apply', action='store_true',
                        help='Modify and rename the files. Without this '
                             'option, only print what would be done.')
    args = parser.parse_args()

    n_fixed = 0
    reprocess = []
    for path in find_files(args.paths):
        try:
            result = fix_file(path, args.apply)
        except Exception as e:
            print('ERROR {}: {}'.format(path, e), file=sys.stderr)
            reprocess.append((path, 'cannot be read: {}'.format(e)))
            continue
        actions, problem, new_path = result
        if problem is not None:
            reprocess.append((path, problem))
        if not actions:
            continue
        n_fixed += 1
        print(path)
        for action in actions:
            print('    ' + action)
        if args.apply and new_path is not None:
            if os.path.exists(new_path):
                print('    NOT renamed: {} already exists'.format(new_path),
                      file=sys.stderr)
            else:
                os.rename(path, new_path)

    print('{} file(s) {}'.format(
        n_fixed, 'fixed' if args.apply else 'to fix (use --apply)'))
    if reprocess:
        print('\nThe following files must be reprocessed with pycordexer:')
        for path, problem in reprocess:
            print('  {}: {}'.format(path, problem))
    return 1 if reprocess else 0


if __name__ == '__main__':
    sys.exit(main())
