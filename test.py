import click
import nclustgen
import numpy
from scipy.sparse import csr_matrix
from sparse import COO
import os
import json
import warnings

@click.command()
@click.option('--GridFile', default=None, help='Path to json file with test parameters grid')
@click.option('--output', default=None, help='How to output if errors exit')
def testcli(GridFile, output):

    if GridFile:
        f = open(GridFile, )
        GridFile = json.load(f)
        f.close()

    errs = Test(grid=GridFile).test()

    if output and errs:

        if output == 'print':
            print(errs)
        else:
            with open('output.json', 'w') as outfile:
                json.dump(errs, outfile)


class Test:

    def __init__(self, grid=None):

        if grid is None:
            grid = {
                'BiclusterGenerator': {
                    'init':
                        {
                            'dstype': {
                                'NUMERIC': {
                                    'patterns': [
                                        ['CONSTANT', 'CONSTANT'],
                                        ['NONE', 'ORDER_PRESERVING'],
                                        ['CONSTANT', 'NONE'],
                                        ['NONE', 'ADDITIVE'],
                                        ['MULTIPLICATIVE', 'CONSTANT'],
                                        None
                                    ],
                                    'realval': [True, False],
                                    'minval:': [2, -30],
                                    'maxval': [15, 20]
                                },
                                'SYMBOLIC': {
                                    'patterns': [
                                        ['CONSTANT', 'CONSTANT'],
                                        ['NONE', 'ORDER_PRESERVING'],
                                        ['CONSTANT', 'NONE'],
                                        None
                                    ],
                                    'symbols': [
                                        [1,2,3,4,5],
                                        ['1', '2', '3'],
                                        None
                                    ],
                                    'nsymbols': [5, None]
                                }
                            },
                            'bktype': {
                                'NORMAL': {
                                    'mean': [10, None],
                                    'sdev': [3, None]
                                },
                                'UNIFORM': None,
                                'MISSING': None
                            },
                            'clusterdistribution': [
                                [['NORMAL', 10, 1], ['UNIFORM', 3, 7]]
                            ],
                            'contiguity': [None, 'COLUMNS'],
                            'plaidcoherency': ['ADDITIVE', 'MULTIPLICATIVE', 'INTERPOLED', 'NONE', 'NO_OVERLAPPING'],
                            'timeprofile': ['RANDOM', 'MONONICALLY_INCREASING', 'MONONICALLY_DECREASING']
                         },
                    'generate': {
                        'nrows': [30],
                        'ncols': [20],
                        'nclusters': [2],
                        'no_return': [True, False],
                        'in_memory': [True, False, None],
                    },
                    'save': {
                        'path': [None],
                        'single_file': [True, False],
                        'file_name': ['test']
                    },
                    'graph': {
                        'framework': ['networkx', 'dgl'],
                        'device': ['cpu', 'gpu']
                    }
                },
                'TriclusterGenerator': {
                    'init':
                        {
                            'dstype': {
                                'NUMERIC': {
                                    'patterns': [
                                        ['NONE', 'NONE', 'ORDER_PRESERVING'],
                                        ['CONSTANT', 'NONE', 'NONE'],
                                        ['CONSTANT', 'CONSTANT', 'MULTIPLICATIVE'],
                                        ['CONSTANT', 'CONSTANT', 'ADDITIVE'],
                                        None
                                    ],
                                    'realval': [True, False],
                                    'minval:': [2, -30],
                                    'maxval': [15, 20]
                                },
                                'SYMBOLIC': {
                                    'patterns': [
                                        ['NONE', 'ORDER_PRESERVING', 'NONE'],
                                        ['CONSTANT', 'NONE', 'NONE'],
                                        None
                                    ],
                                    'symbols': [
                                        [1, 2, 3, 4, 5],
                                        ['1', '2', '3'],
                                        None
                                    ],
                                    'nsymbols': [5, None]
                                }
                            },
                            'bktype': {
                                'NORMAL': {
                                    'mean': [10, None],
                                    'sdev': [3, None]
                                },
                                'UNIFORM': None,
                                'MISSING': None
                            },
                            'clusterdistribution': [
                                [['NORMAL', 10, 1], ['UNIFORM', 3, 7], ['NORMAL', 10, 1]]
                            ],
                            'contiguity': [None, 'COLUMNS', 'CONTEXTS'],
                            'plaidcoherency': ['ADDITIVE', 'MULTIPLICATIVE', 'INTERPOLED', 'NONE', 'NO_OVERLAPPING'],
                            'timeprofile': ['RANDOM', 'MONONICALLY_INCREASING', 'MONONICALLY_DECREASING']
                        },
                    'generate': {
                        'nrows': [30],
                        'ncols': [20],
                        'ncontexts': [3],
                        'nclusters': [2],
                        'no_return': [True, False],
                        'in_memory': [True, False, None],
                    },
                    'save': {
                        'path': [None],
                        'single_file': [True, False],
                        'file_name': ['test']
                    },
                    'graph': {
                        'framework': ['networkx', 'dgl'],
                        'device': ['cpu', 'gpu']
                    }
                }
            }

        self.grid = grid

        # error collector
        self.description = []

    def test(self):

        combinations = self.__grid_parser(self.grid)

        for n, combination in enumerate(combinations):

            self.description.append({
                'test': n,
                'params': combination,
                'errors': []
            })

            try:
                instance = getattr(nclustgen, combination['algorithm'])(combination['init'])

                try:
                    self.__test_generate(instance, combination['generate'])
                except Exception as err:
                    self.__error_collector(err, 'generate crash')

                try:
                    self.__test_save(instance, combination['save'])
                except Exception as err:
                    self.__error_collector(err, 'save crash')

                try:
                    self.__test_graph(instance, combination['graph'])
                except Exception as err:
                    self.__error_collector(err, 'graph crash')

            except Exception as err:
                self.__error_collector(err, 'init crash')

            if len(self.description[-1]['errors']) == 0:
                self.description.pop()

        if len(self.description) > 0:
            warnings.warn('{} errors occurred'.format(len(self.description)))

        return self.description

    @staticmethod
    def __grid_parser(grid):
        # TODO implement grid parser

        combinations = []  # parsed grid

        return combinations

    def __test_generate(self, instance, params):

        x, y = instance.generate(**params)

        if params['no_return']:
            try:
                assert x is None
                assert y is None
                assert instance.generatedDataset

            except Exception as err:
                self.__error_collector(err, 'test no_return on generator')

        else:
            self.__test_tensor(
                shape=(params['nrows'], params['ncols'], params['ncontexts']),
                clusters=params['nclusters'],
                x=x,
                y=y,
                memory=params['memory'],
                n=instance.n
            )

    def __test_tensor(self, shape, clusters, x, y, memory, n):

        try:
            assert isinstance(y, list)
            assert len(y) == clusters

            if memory:
                assert isinstance(x, numpy.ndarray)

            else:
                assert isinstance(x, csr_matrix) and n == 2 or isinstance(x, COO) and n == 3

            if (x.shape != shape and n == 3) or (x.shape != shape[1:] and n == 2):
                raise AssertionError('wrong dataset shape ... {} expected: {}'.format(x.shape, shape))

        except Exception as err:
            self.__error_collector(err, 'tests on tensor')

    def __test_save(self, instance, params):

        instance.save(**params)

        if params['path'] is None:
            params['path'] = os.getcwd()

        if instance.asses_memory(params['single_file'], gends=instance.generatedDataset):
            suffix = ''
        else:
            suffix = '_1'

        assert '{}_data{}.tsv'.format(params['file_name'], suffix) in os.listdir(params['path'])

        if instance.n == 2:
            alg = 'bics'

        else:
            alg = 'trics'

        for suffix in ['json', 'txt']:
            assert '{}_{}.{}'.format(params['file_name']) in os.listdir(params['path'])

    def __test_graph(self, instance, params):
        # TODO implement graph tests
        pass

    def __error_collector(self, err, description):

        self.description[-1]['errors'].append({
            'error': repr(err), 'description': description
        })


if __name__ == '__main__':
 testcli()
