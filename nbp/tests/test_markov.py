import nbp
import numpy as np
import numpy.testing as npt

from .tools import make_system


def test_optimize_lj_finds_local_minimum():
    characteristic_length = 20
    particle_count = 10
    system = make_system(characteristic_length=characteristic_length,
                         particle_count=particle_count,
                         lj=True,
                         ewald=False,
                         use_neighbours=False)
    system.optimize()

    e_last_except_extreme = np.asarray([system.states()[i].energy() for i in range(-2, -5, -1)])
    e_last_extreme = np.ones_like(e_last_except_extreme) * system.state().energy()

    npt.assert_almost_equal(e_last_except_extreme, e_last_extreme)


# def test_optimize_lj_finds_tetrahedron():
#     characteristic_length = 10
#     particle_count = 4
#     system = make_system(characteristic_length=characteristic_length,
#                          particle_count=particle_count,
#                          lj=True,
#                          ewald=False,
#                          use_neighbours=False)
#     system.optimize()
#
#     tetrahedron_dist = np.array([[ 0.        ,  6.79176036,  4.16560376,  6.5014517 ],
#                                  [ 6.79176036,  0.        ,  6.87371615,  1.84749012],
#                                  [ 4.16560376,  6.87371615,  0.        ,  6.12528527],
#                                  [ 6.5014517 ,  1.84749012,  6.12528527,  0.        ]])
#
#     npt.assert_almost_equal(system.state().distances_wrapped(), tetrahedron_dist)



def test_simulate():
    # Compare two particle monte carlo to two particle mcmc.
    pass
