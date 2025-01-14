#!/usr/local/lcls/package/python/current/bin/python
################################################################################
# Modified version of John Sheppard's read_xcor_data script
# Reads in a matlab file of xcor data and fits gaussians to it
# Data must have column names posList, ampList, and ampstdList
################################################################################

from __future__ import division

from pylab import array, plt, floor, show
from numpy import argsort, power, exp, zeros
from scipy.io import loadmat
from scipy.optimize import curve_fit
from operator import itemgetter
from sys import argv, exit
from time import time

NUM_BUCKS = 10
DEBUG = False


# An unfortunate consequence of defining step as max/numbucks is that the
# maximum point is in its own bucket (bucket 10), which would break a lot of 
# shit, so it necessitates the error checking
def get_bucket(val, step):
    bucket = int(floor(val / step))
    return bucket if bucket < 10 else 9


def find_max(data, run):
    max_index = max(enumerate(data[run]), key=itemgetter(1))[0]
    return run[max_index]


# The very ham-fisted way I'm coming up with a guess for the width of a given
# peak is to get the literal distance between the first element of the
# subsequent run and the last element of the previous run
def find_widths(xdata, peak_idxs, runs, run_map):
    widths = []
    for peak_idx in peak_idxs:
        run_idx = run_map[peak_idx]

        # If it's the first run, just double the distance between the peak and
        # the first element of the next run
        if run_idx == 0:
            widths.append((xdata[runs[1][0]] - xdata[peak_idx]) * 2)

        # If it's the last run, just double the distance between the peak and
        # the last element of the previous run
        elif run_idx == len(runs) - 1:
            widths.append((xdata[peak_idx] - xdata[runs[-2][-1]]) * 2)

        else:
            widths.append(
                xdata[runs[run_idx + 1][0]] - xdata[runs[run_idx - 1][-1]])

    return widths


# Modified from StackOverflow
def gen_gauss_sum(x, *params):
    m = params[0]
    b = params[1]

    y = [m * i + b for i in x]

    for i in range(2, len(params), 3):
        ctr = params[i]
        amp = params[i + 1]
        wid = params[i + 2]
        y = y + gaussian(x, ctr, wid, amp)
    return y

def gaussian(x, ctr, wid, amp):
    return amp * exp(-power(x - ctr, 2.) / (2 * power(wid, 2.)))


def get_slope(x1, y1, x2, y2):
    return (y2 - y1) / (x2 - x1)


# Idea to add a line instead of a really short, fat gaussian was all Ahemd.
# Thanks, yo. You're great.
def find_line(zero_runs, runs, xdata, ydata):
    x1, y1, x2, y2, m, b = (0, 0, 0, 0, 0, 0)

    # This condition should only be possible if there are peaks on one or both 
    # extremes, or if there is no peak
    if len(zero_runs) == 1:
        zeroRun = runs[zero_runs[0]]
        # This should pull out the median index value of the run
        x_ind1 = zero_run[argsort(ydata[zero_run])[len(zero_run) / 2]]
        y1 = ydata[x_ind1]

        return [m, y1]

    # 0 shouldn't be possible given that the data is normalized to the lowest 
    # point, so it should otherwise be at least 2.
    # Currently just fitting the first point of the first zero run and the last
    # point of the last zero run. Could make it smarter by adding a sum of step
    # functions, but that seems like overkill
    else:
        zero1 = runs[zero_runs[0]]
        zero2 = runs[zero_runs[-1]]
        
        x_ind1 = zero1[argsort(ydata[zero1])[int(len(zero1) / 2)]]
        x1 = xdata[x_ind1]
        y1 = ydata[x_ind1]

        x_ind2 = zero2[argsort(ydata[zero2])[int(len(zero2) / 2)]]
        x2 = xdata[x_ind2]
        y2 = ydata[x_ind2]

        m = get_slope(x1, y1, x2, y2)

        return [m, y1 - m * x1]


# Every run has the potential to be a peak, but we limit it to the numPeaks
# largest ones
def get_peaks(data, num_peaks, runs):
    # Should be doable in preprocessing
    len_runs = map(lambda run: len(run), runs)

    # User-proofing. Could probably limit input
    num_peaks = num_peaks if num_peaks <= len(runs) else len(runs)

    # Would be using linear argpartsort if we were running not 2013 builds.
    # Can you tell I'm bitter?
    ind = argsort(array(len_runs))[-num_peaks:]

    # This is inelegant
    peak_idx, peaks = ([], [])
    for run in array(runs)[ind]:
        idx = find_max(data, run)
        peak_idx.append(idx)
        peaks.append(data[idx])

    max_index, max_value = max(enumerate(data), key=itemgetter(1))

    # Maybe unnecessary precaution to make sure that the max point is used in
    # the fit (a run wouldn't be found if the peak were sufficiently narrow)
    max_info = []
    if max_value not in peaks:
        if peaks:
            min_index = min(enumerate(peaks), key=itemgetter(1))[0]
            peaks[min_index] = max_value
            peak_idx[min_index] = max_index
        else:
            peak_idx.append(max_index)
            peaks.append(max_value)
            max_info = [max_index, max_value]

    return [peaks, peak_idx, max_info]


# Checking for inflection points doesn't work because some data points don't 
# follow the trend line; this groups consecutive data points by bucket, which
# need to be recalculated following an adjustment.
def get_runs(data, step):
    # runMap maps each data point to the run that contains it
    zero_runs, non_zero_runs, runs, curr_run, run_map = ([], [], [], [], [])
    curr_buck = get_bucket(data[0], step)
    run_idx = 0

    for idx, point in enumerate(data):
        new_buck = get_bucket(point, step)
        if new_buck == curr_buck:
            curr_run.append(idx)
        else:
            # Plotting the end of a run
            if DEBUG:
                plt.axvline(x=idx)

            # Three points make a curve!
            if len(curr_run) > 2:
                runs.append(curr_run)
                run_idx += 1
                if curr_buck == 0:
                    zero_runs.append(len(runs) - 1)
                else:
                    non_zero_runs.append(curr_run)

            curr_run = [idx]
            curr_buck = new_buck

        run_map.append(run_idx)

    # Effectively flushing the cache. There has to be a way to factor this out
    if len(curr_run) > 2:
        runs.append(curr_run)
        if curr_buck == 0:
            zero_runs.append(len(runs) - 1)
        else:
            non_zero_runs.append(currRun)

    return [runs, zero_runs, non_zero_runs, run_map]


# A whole rigmarole to collapse multiple pedestals.
# It assumes that the pedestal is the bucket with the most elements
def adjust_data(data, step):
    start = time()
    normalized_adjustment = 0

    bucket_count = zeros(NUM_BUCKS)
    bucket_contents = [[] for i in range(0, NUM_BUCKS)]
    buckets = zeros(len(data))

    for idx, element in enumerate(data):
        bucket = get_bucket(element, step)
        bucket_count[bucket] += 1
        bucket_contents[bucket] += [idx]
        buckets[idx] = bucket

    zero_bucket = max(enumerate(bucket_count), key=itemgetter(1))[0]

    needs_adjustment = False

    for idx, bucket in enumerate(buckets):
        if bucket < zero_bucket:
            # Inefficient to set this every time, but eh
            needs_adjustment = True
            # Sets them arbitrarily to the value of the first element in the
            # zero bucket, to eliminate the double pedestal
            data[idx] = data[bucket_contents[zero_bucket][0]]

    if needs_adjustment:
        normalized_adjustment = min(data[bucket_contents[zero_bucket]])
        data = data - normalized_adjustment
        step = max(data) / NUM_BUCKS

    return [data, step, normalized_adjustment]


################################################################################
# So this is a giant clusterfuck of logic where I try to autodetect peaks by 
# detecting "runs" of points, defined as a group of 3 or more consecutive points
# that belong to the same  bucket, while simultaneously tagging those runs that
# belong to the "zeroeth" bucket (the pedestal).
#
# Note that the format of the guess is a list of the form:
# [m, b, center_0, amplitude_0, width_0,..., center_k, amplitude_k, width_k]
# where m and b correspond to the line parameters in y = m*x + b
# and every following group of three corresponds to a gaussian
################################################################################ 
def get_guess(xdata, ydata, step, use_zeros, num_peaks):
    runs, zero_runs, non_zero_runs, run_map = get_runs(ydata, step)

    peaks, peak_idx, max_info = (get_peaks(ydata, num_peaks, non_zero_runs)
                               if not use_zeros
                               else get_peaks(ydata, num_peaks, runs))

    # Gross error handling for the case where the max val isn't detected as a
    # peak (making sure it's added to runs in the correct order)
    if max_info:
        max_idx = max_info[0]
        if run_map[max_idx] >= len(runs):
            runs.append(max_idx)
        else:
            runs[run_map[max_idx]].append(max_idx)

    # This plots my guesses for the peaks
    if DEBUG:
        for idx in peak_idx:
            plt.axvline(x=idx)

    # Should rethink widths calculation, it's usually about 1/5 of acutal,
    # which means the algorithm needs more iterations to get closer.
    widths = find_widths(xdata, peak_idx, runs, run_map)

    guess = find_line(zero_runs, runs, xdata, ydata)

    # This plots my guess for the line
    if DEBUG:
        plt.plot([guess[0] * j + guess[1] for j in xdata], '--')

    for idx, amp in enumerate(peaks):
        guess += [xdata[peak_idx[idx]], amp, widths[idx] / 4]

        # Plot my initial guesses for the gaussian(s)
        if DEBUG:
            plt.plot([gaussian(i, xdata[peak_idx[idx]], widths[idx] / 4, amp)
                      for i in xdata], '--')

    return [guess, len(runs) if use_zeros else len(non_zero_runs)]


def process_data(data):
    first_adjustment = min(data)

    # Removing the pedestal
    data = data - first_adjustment

    # Define the step size by the number of vertical buckets
    step = max(data) / NUM_BUCKS

    data, step, normalized_adjustment = adjust_data(data, step)

    # This prints my vertical buckets
    if DEBUG:
        for i in range(1, NUM_BUCKS):
            plt.plot([i * step for _ in range(0, len(data))])

    total_adjustment = first_adjustment + normalized_adjustment

    return [data, total_adjustment, step]


def get_fit(data, x, guess):
    # Someday the ability to bound the fit will be available...
    # ...When we're no longer running builds from 2013 :P
    return curve_fit(gen_gauss_sum, x, data, p0=guess)[0]



