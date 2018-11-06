import unittest
import numpy as np
import random

from math import log10
import pytest

from multivar_horner import HornerMultivarPolynomial, MultivarPolynomial, get_prime_array

import timeit


def proto_test_case(data, fct):
    all_good = True
    for input, expected_output in data:
        # print(input, expected_output, fct(input))
        actual_output = fct(input)
        if actual_output != expected_output:
            print('input: {} expected: {} got: {}'.format(input, expected_output, actual_output))
            all_good = False

    assert all_good


#
# def id2exponent_vect(prime_list, monomial_id):
#     # find the exponent vector corresponding to a monomial id
#     # = prime decomposition
#     exponent_vect = np.zeros(prime_list.shape, dtype=np.uint)
#     current_id = monomial_id
#     for i, prime in enumerate(prime_list):
#         while 1:
#             quotient, remainder = divmod(current_id, prime)
#             if remainder == 0:
#                 exponent_vect[i] += 1
#                 current_id = quotient
#             else:
#                 break
#
#         if current_id == 0:
#             break
#
#     if current_id != 0:
#         raise ValueError('no factorisation found')
#
#     return exponent_vect
#
#
# def _sparse_range_generator(max_value, density):
#     for i in range(max_value):
#         if random.random() < density:
#             yield i


def random_polynomial_settings(all_exponents, max_abs_coeff=1.0):
    # every exponent can take the values in the range [0; max_degree]
    max_nr_exponent_vects = all_exponents.shape[0]

    # decide how many entries the polynomial should have
    # desired for meaningful speed test results:
    # every possible polynomial should appear with equal probability
    # there must be at least 1 entry
    nr_exponent_vects = random.randint(1, max_nr_exponent_vects)

    row_idxs = list(range(max_nr_exponent_vects))
    assert max_nr_exponent_vects >= nr_exponent_vects
    for length in range(max_nr_exponent_vects, nr_exponent_vects, -1):
        # delete random entry from list
        row_idxs.pop(random.randint(0, length - 1))

    assert len(row_idxs) == nr_exponent_vects

    exponents = all_exponents[row_idxs, :]
    coefficients = (np.random.rand(nr_exponent_vects, 1) - 0.5) * (2 * max_abs_coeff)
    return coefficients, exponents


def all_possible_exponents(dim, max_degree):
    def cntr2exp_vect(cntr):
        exp_vect = np.empty((dim), dtype=np.uint)
        for d in range(dim - 1, -1, -1):
            divisor = (max_degree + 1) ** d
            # cntr = quotient*divisor + remainder
            quotient, remainder = divmod(cntr, divisor)
            exp_vect[d] = quotient
            cntr = remainder
        return exp_vect

    max_nr_exponent_vects = (max_degree + 1) ** dim
    all_possible = np.empty((max_nr_exponent_vects, dim), dtype=np.uint)
    for i in range(max_nr_exponent_vects):
        # print(i, cntr2exp_vect(i))
        all_possible[i] = cntr2exp_vect(i)

    return all_possible


def rnd_settings_list(length, dim, max_degree):
    all_exponent_vect = all_possible_exponents(dim, max_degree)
    settings_list = [random_polynomial_settings(all_exponent_vect) for i in range(length)]

    # # random settings should have approx. half the amount of maximal entries on average
    # num_monomial_entries = 0
    # for settings in settings_list:
    #     num_monomial_entries += settings[0].shape[0]
    #
    # avg_monomial_entries = num_monomial_entries / length
    # max_monomial_entries = int((max_degree + 1) ** dim)
    # print(avg_monomial_entries, max_monomial_entries)
    return settings_list


def rnd_input_list(length, dim, max_abs_val):
    return [(np.random.rand(dim) - 0.5) * (2 * max_abs_val) for i in range(length)]


def setup_time_fct(poly_class):
    # store instances globally to directly use them for eval time test
    global poly_settings_list, poly_class_instances

    poly_class_instances = []
    for settings in poly_settings_list:
        poly_class_instances.append(poly_class(*settings))


def eval_time_fct():
    global poly_class_instances, input_list

    for instance, input in zip(poly_class_instances, input_list):
        instance.eval(input)


def print_avg_num_ops():
    global poly_class_instances

    num_ops = 0
    for instance in poly_class_instances:
        num_ops += instance.num_ops()

    avg_num_ops = round(num_ops / len(poly_class_instances))
    print(avg_num_ops)


def time_preprocess(time):
    valid_digits = 4
    zero_digits = abs(min(0, int(log10(time))))
    digits_to_print = zero_digits+valid_digits
    return str(round(time, digits_to_print))


poly_settings_list = []
input_list = []
poly_class_instances = []


class MainTest(unittest.TestCase):

    def test_eval(self):
        def cmp_value_fct(inp):
            print()
            coeff, exp, x = inp
            x = np.array(x).T
            poly = MultivarPolynomial(coeff, exp, rectify_input=True, validate_input=True)
            res1 = poly.eval(x, validate_input=True)
            print(str(poly))

            horner_poly = HornerMultivarPolynomial(coeff, exp, rectify_input=True, validate_input=True)
            res2 = horner_poly.eval(x, validate_input=True)
            print(str(horner_poly))
            if res1 != res2:
                print('resutls differ:', res1, res2)

            return poly.eval(x, validate_input=True)

        invalid_test_data = [
            # calling with x of another dimension
            (([1.0, 2.0, 3.0],
              [[3, 1, 0], [2, 0, 1], [1, 1, 1]],
              [-2.0, 3.0, ]),
             # p(x) = 5.0 + 2.0* (-2)^1 + 1.0* (-2)^2 + 2.0* (-2)^2 *3^1 = 5.0 + 2.0* (-2) + 1.0* 4 + 2.0* 4 *3
             29.0),

            (([1.0, 2.0, 3.0],
              [[3, 1, 0], [2, 0, 1], [1, 1, 1]],
              [-2.0, 3.0, 1.0, 4.0]),
             # p(x) = 5.0 + 2.0* (-2)^1 + 1.0* (-2)^2 + 2.0* (-2)^2 *3^1 = 5.0 + 2.0* (-2) + 1.0* 4 + 2.0* 4 *3
             29.0),

            # negative exponents are not allowed
            (([1.0, 2.0, 3.0],
              [[3, -1, 0], [2, 0, 1], [1, 1, 1]],
              [-2.0, 3.0, 1.0, 4.0]),
             # p(x) = 5.0 + 2.0* (-2)^1 + 1.0* (-2)^2 + 2.0* (-2)^2 *3^1 = 5.0 + 2.0* (-2) + 1.0* 4 + 2.0* 4 *3
             29.0),

            # duplicate exponent entries are not allowed
            # negative exponents are not allowed
            (([1.0, 2.0, 3.0],
              [[3, 1, 0], [3, 1, 0], [2, 0, 1], [1, 1, 1]],
              [-2.0, 3.0, 1.0, 4.0]),
             # p(x) = 5.0 + 2.0* (-2)^1 + 1.0* (-2)^2 + 2.0* (-2)^2 *3^1 = 5.0 + 2.0* (-2) + 1.0* 4 + 2.0* 4 *3
             29.0),

        ]

        for inp, expected_output in invalid_test_data:
            with pytest.raises(AssertionError):
                cmp_value_fct(inp)

        invalid_test_data = [
            #
            # p(x) =  5.0
            (([5.0],  # coefficients
              [0],  # exponents
              [0.0]),  # x
             5.0),  # p(x)

            # p(1.0) = 1.0
            (([5.0],
              [0],
              [1.0]),
             5.0),

            # p(-1.0) = -1.0
            (([5.0],
              [0],
              [-1.0]),
             5.0),

            # p(33.5) =33.5
            (([5.0],
              [0],
              [33.5]),
             5.0),

            # p(x) =  1.0* x_1^1
            # p(0.0) = 0.0
            (([1.0],  # coefficients
              [1],  # exponents
              [0.0]),  # x
             0.0),  # p(x)

            # p(1.0) = 1.0
            (([1.0],
              [1],
              [1.0]),
             1.0),

            # p(-1.0) = -1.0
            (([1.0],
              [1],
              [-1.0]),
             -1.0),

            # p(33.5) =33.5
            (([1.0],
              [1],
              [33.5]),
             33.5),

            # p(x) =  1.0* x_1^1 + 0.0* * x_2^1
            (([1.0, 0.0],
              [[1, 0], [0, 1]],
              [0.0, 0.0]),
             0.0),

            (([1.0, 0.0],
              [[1, 0], [0, 1]],
              [1.0, 0.0]),
             1.0),

            (([1.0, 0.0],
              [[1, 0], [0, 1]],
              [-1.0, 0.0]),
             -1.0),

            (([1.0, 0.0],
              [[1, 0], [0, 1]],
              [33.5, 0.0]),
             33.5),

            # p(x) =  5.0 +  1.0* x_1^1
            (([5.0, 1.0],
              [[0, 0], [1, 0]],
              [0.0, 0.0]),
             5.0),

            (([5.0, 1.0],
              [[0, 0], [1, 0]],
              [1.0, 0.0]),
             6.0),

            (([5.0, 1.0],
              [[0, 0], [1, 0]],
              [-1.0, 0.0]),
             4.0),

            (([5.0, 1.0],
              [[0, 0], [1, 0]],
              [33.5, 0.0]),
             38.5),

            # p(x) =  5.0 + 2.0* x_1^1 + 1.0* x_1^2
            (([5.0, 2.0, 1.0],
              [[0, 0], [1, 0], [2, 0]],
              [0.0, 0.0]),
             5.0),

            (([5.0, 2.0, 1.0],
              [[0, 0], [1, 0], [2, 0]],
              [1.0, 0.0]),
             8.0),  # p(x) =  5.0 + 2.0 + 1.0

            (([5.0, 2.0, 1.0],
              [[0, 0], [1, 0], [2, 0]],
              [-1.0, 0.0]),
             4.0),  # p(x) =  5.0 - 2.0 + 1.0

            (([5.0, 2.0, 1.0],
              [[0, 0], [1, 0], [2, 0]],
              [2.0, 0.0]),
             13.0),  # p(x) =  5.0 + 2.0* 2.0^1 + 1.0* 2.0^2

            # p(x) =  5.0 + 2.0* x_1^1 + 1.0* x_1^2 + 2.0* x_1^2 *x_2^1
            (([5.0, 2.0, 1.0, 2.0],
              [[0, 0], [1, 0], [2, 0], [2, 1]],
              [0.0, 0.0]),
             5.0),

            (([5.0, 2.0, 1.0, 2.0],
              [[0, 0], [1, 0], [2, 0], [2, 1]],
              [1.0, 0.0]),
             8.0),  # p(x) =  5.0 + 2.0* 1^1 + 1.0* 1^2 + 2.0* 1^2 *0^1

            (([5.0, 2.0, 1.0, 2.0],
              [[0, 0], [1, 0], [2, 0], [2, 1]],
              [1.0, 1.0]),
             10.0),  # p(x) =  5.0 + 2.0* 1^1 + 1.0* 1^2 + 2.0* 1^2 *1^1

            (([5.0, 2.0, 1.0, 2.0],
              [[0, 0], [1, 0], [2, 0], [2, 1]],
              [-1.0, 0.0]),
             4.0),  # p(x) =  5.0 + 2.0* (-1)^1 + 1.0* (-1)^2 + 2.0* (-1)^2 *0^1

            (([5.0, 2.0, 1.0, 2.0],
              [[0, 0], [1, 0], [2, 0], [2, 1]],
              [-1.0, 1.0]),
             6.0),  # p(x) =  5.0 + 2.0* (-1)^1 + 1.0* (-1)^2 + 2.0* (-1)^2 *1^1

            (([5.0, 2.0, 1.0, 2.0],
              [[0, 0], [1, 0], [2, 0], [2, 1]],
              [-1.0, 2.0]),
             8.0),  # p(x) =  5.0 + 2.0* (-1)^1 + 1.0* (-1)^2 + 2.0* (-1)^2 *2^1

            (([5.0, 2.0, 1.0, 2.0],
              [[0, 0], [1, 0], [2, 0], [2, 1]],
              [-1.0, 3.0]),
             10.0),  # p(x) =  5.0 + 2.0* (-1)^1 + 1.0* (-1)^2 + 2.0* (-1)^2 *3^1

            (([5.0, 2.0, 1.0, 2.0],
              [[0, 0], [1, 0], [2, 0], [2, 1]],
              [-2.0, 3.0]),
             # p(x) = 5.0 + 2.0* (-2)^1 + 1.0* (-2)^2 + 2.0* (-2)^2 *3^1 = 5.0 + 2.0* (-2) + 1.0* 4 + 2.0* 4 *3
             29.0),

            # [20] p(x) = 1.0 x_1^3 x_2^1 + 2.0 x_1^2 x_3^1 + 3.0 x_1^1 x_2^1 x_3^1
            # [17] p(x) = x_2^1 [ x_1^3 [ 1.0 ] + x_1^1 x_3^1 [ 3.0 ] ] + x_1^2 x_3^1 [ 2.0 ]
            (([1.0, 2.0, 3.0],
              [[3, 1, 0], [2, 0, 1], [1, 1, 1]],
              [-2.0, 3.0, 1.0]),
             -34.0),

            # [27] p(x) = 1.0 x_3^1 + 2.0 x_1^3 x_2^3 + 3.0 x_1^2 x_2^3 x_3^1 + 4.0 x_1^1 x_2^5 x_3^1
            (([1.0, 2.0, 3.0, 4.0],
              [[0, 0, 1], [3, 3, 0], [2, 3, 1], [1, 5, 1], ],
              [-2.0, 3.0, 1.0]),
             -2051.0),
        ]

        proto_test_case(invalid_test_data, cmp_value_fct)

    def test_speed(self):

        def speed_up(time1, time2):
            speedup = round((time2 / time1 - 1), 2)
            if speedup < 0:
                speedup = round((time1 / time2 - 1), 2)
                return str(speedup) + ' x slower'
            else:
                return str(speedup) + ' x faster'

        global poly_settings_list, input_list, poly_class_instances

        MAX_DIM = 5
        MAX_DEGREE = 5
        NR_SAMPLES = 200

        # TODO compare difference in computed values (error)
        # todo print to file
        template = '{0:3s} | {1:7s} | {2:16s} | {3:17s} | {4:15s} | {5:16s} | {6:16s} | {7:15s}'

        print('\nSpeed test:')
        # TODO num ops
        print(template.format('dim', 'max_deg', 'setup time naive', 'setup time horner', 'delta', 'eval time naive',
                              'eval time horner', 'delta'))
        print('=' * 120)

        for dim in range(1, MAX_DIM + 1):
            for max_degree in range(1, MAX_DEGREE + 1):
                poly_settings_list = rnd_settings_list(NR_SAMPLES, dim, max_degree)
                input_list = rnd_input_list(NR_SAMPLES, dim, max_abs_val=1.0)

                setup_time_naive = timeit.timeit("setup_time_fct(MultivarPolynomial)", globals=globals(), number=1)
                # poly_class_instances is not populated with the naive polynomial class instances
                # print(poly_class_instances[0])
                # print_avg_num_ops()
                # FIXME too few monomials! often just one empty exponent

                eval_time_naive = timeit.timeit("eval_time_fct()", globals=globals(), number=1)

                setup_time_horner = timeit.timeit("setup_time_fct(HornerMultivarPolynomial)", globals=globals(),
                                                  number=1)
                # poly_class_instances is not populated with the horner polynomial class instances
                # print(poly_class_instances[0])
                # print_avg_num_ops()

                eval_time_horner = timeit.timeit("eval_time_fct()", globals=globals(), number=1)

                setup_delta = speed_up(setup_time_horner, setup_time_naive)
                eval_delta = speed_up(eval_time_horner, eval_time_naive)

                print(template.format(str(dim), str(max_degree), time_preprocess(setup_time_naive),
                                      time_preprocess(setup_time_horner),
                                      str(setup_delta),
                                      time_preprocess(eval_time_naive), time_preprocess(eval_time_horner),
                                      str(eval_delta), ))

            print()


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(MainTest)
    unittest.TextTestRunner(verbosity=2).run(suite)
    unittest.main()
