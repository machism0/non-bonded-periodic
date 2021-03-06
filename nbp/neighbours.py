import numpy as np
import math
import collections


def periodic_particles_stay_in_box(pos_arr, length):
    return pos_arr - np.floor(pos_arr / length) * length


def periodic_wrap_corner(dist_arr, length, verbose=False):
    """For a box with lower left vertex at the origin."""
    if verbose:
        print(dist_arr)
    dist_arr = dist_arr - np.around(dist_arr / length) * length
    if verbose:
        print(dist_arr)
    return dist_arr


class Neighbours:
    """
    This class is used to evaluate the position of
    particles to each others. The system must be big enough to
    contain at least 3 subcells per row.
    
    Private Functions:
    __init__, _create_subcells, _create_neighbours, _find_subcell, 
    _neighbours_for_one, _create_neigbours_frame, _get_neighbours_frame,
    _get_neighbour_subcell, _3d_subcell_id, _cell_y, _cell_z
    
    Public Functions:
    update_neighbours, get_neighbours

    """
    def __init__(self, system_info, system_state, system, verbose=False):
        """
        Instantiates a new Object of class Neighbours.
        
        :param system_info: Instance of class System Info
        :param system_state: Instance of class System State
        :param system: Instance of class System
        :param verbose: boolean (default: False)
                        Indicates if output of Neighbours should be printed.
        """
        self._verbose = verbose
        self.SystemInfo = system_info
        self.SystemState = system_state
        self.System = system
        self._box_length = self.SystemInfo.char_length()
        self._skin_radius = self.SystemInfo.worse_sigma() * 3
        # The 3 is just an option that mostly works (?)
        self._subcells_inrow = 1
        self._subcell_length = self._create_subcells()
        self._neighbour_list = self._create_neighbours()

        # Empty frame for the neighbours
        self._neighbours_frame_IDs = None
        self._neighbours_frame_dist = None
        self._create_neighbours_frame()

        # variables needed for update
        self._last_update = 0
        self._update_count = 0

        pass

    def _create_subcells(self):
        """
        Calculates the length of the subcells based on the skin radius.
        This helps to avoid having to update every time.
        
        :return: length of subcell
        """
        # calculate subcell size.
        while self._skin_radius < self._box_length / self._subcells_inrow:
            self._subcells_inrow += 1

        if self._verbose:
            print("Number of subcells per row:", self._subcells_inrow)
        subcell_length = self._box_length / self._subcells_inrow

        return subcell_length

    def _create_neighbours(self):
        """
        Creates the neighbours list by creating a head list which
        contains the starting index for the particles in a box.
        The neighbour list itself contains the index of the particles
        which belong to each box.
        
        :return: neighbour list
        """
        # get number of particles in the system
        particle_number = self.SystemState.positions().shape[0]

        # create list (head) for starting index of subcell.
        # **3 because we have 3 dimensions for 2 it would be **2.
        self._start_index = [-1] * (self._subcells_inrow**3)

        # create linked neighbour list
        self._neighbour_list = [-1] * particle_number

        # get positions of all particles
        positions = self.SystemState.positions()
        # Find list of particles each subcell contains
        for i in range(particle_number):

            subcell_id = self._find_subcell(positions[i])

            try:
                self._neighbour_list[i] = int(self._start_index[subcell_id])
                self._start_index[subcell_id] = int(i)
            except IndexError:
                pass

        return self._neighbour_list

    def _find_subcell(self, position):
        """
        Private module of object neighbours. Finds the number of the
        subcell in which a particle is positioned.
        
        :param position: position of a particle
        
        :return: subcell_id
        """

        subcell_id_3d = [0, 0, 0]
        # calculate the subcell ID for each axis (x, y, z)
        for axis in range(3):
            try:
                subcell_id_3d[axis] = math.floor(position[axis]
                                                 / self._subcell_length)
            except OverflowError:
                pass

        # Use 3d subcell ID to get the 1d ID
        if (subcell_id_3d[0] < 0 or subcell_id_3d[1] < 0
                or subcell_id_3d[2] < 0):
            raise ValueError('subcell_id value is negative')
        else:
            m = self._subcells_inrow
            subcell_id = subcell_id_3d[0] \
                         + (subcell_id_3d[1] * m) \
                         + (subcell_id_3d[2] * (m ** 2))

        return subcell_id

    @property
    def update_neighbours(self):
        """
        Updates the neighbour list with the new system_state.
        Update of list is only done if the particle have moved far enough.
        Update of the dictionary "neighbours_frame" is done every time.
        System state (e.g. box length etc) should be the same.
        
        :return: new neighbour list
        """
        # update the frame each time:
        self._create_neighbours_frame()

        # get positions from last update
        positions_old = self.System.states()[self._last_update].positions()
        # get current positions
        positions_current = self.System.state().positions()
        if self._verbose:
            print("type positions old:", type(positions_current) )
            print("positions old:", positions_current)

        movement = np.sqrt(positions_old**2 - positions_current**2)
        if self._verbose:
            print("movement:", movement)
        # if movement of particle is far enough that it could be
        # new neighbour then update system.
        if np.max(movement) > (self._skin_radius - self.SystemInfo.cutoff()):
            self._neighbour_list = self._create_neigbours
            self._last_update = self._update_count
            if self._verbose:
                print("updated list")

        self._update_count = + 1

        return self._neighbour_list


    def _neighbours_for_one(self, particle_ID):
        """
        Calculate which neighbours are around the particle.
        Calculates the distance between a particle and its neighbours.
        
        :param particle_ID: particle ID from system 
        
        :return: named tuple containing list of neighbour particles ID and distances
        """
        positions = self.SystemState.positions()
        particle_pos = positions[particle_ID]
        neighbours = []  # neighbour positions
        neighbours_distance = []  # distance of particle to each neighbour
        new_neighbours = []  # only neighbours within cutoff radius
        neighbour_subcells = self._get_neighbours_subcells(particle_pos)
        # get starting positions for each subcell
        start_array = np.asarray(self._start_index)

        # get all particles from the neighbour subcells
        # np.nditer did not work for neighbour_subcells
        # for i in np.nditer(neighbour_subcells):
        # print("neighbour subcells:", neighbour_subcells)
        for i in range(27):
            i = neighbour_subcells[i]
            index = int(start_array[i])

            while index >= 0:
                neighbours.append(index)
                index = int(self._neighbour_list[index])

        nb_length = np.shape(neighbours)[0]

        # get distance from particle to neighbours
        for i in range(nb_length):
            index = neighbours[i]
            # only do this calculation for distances that have not been calculated before
            if index > particle_ID:
                x_distance = abs(particle_pos[0] - positions[index][0])
                y_distance = abs(particle_pos[1] - positions[index][1])
                z_distance = abs(particle_pos[2] - positions[index][2])

                # correct boundary subcells distance.
                l = 2 * self._subcell_length  # max possible distance
                if x_distance > l:
                    x_distance = self._box_length - x_distance
                if y_distance > l:
                    y_distance = self._box_length - y_distance
                if z_distance > l:
                    z_distance = self._box_length - z_distance

                distance_3d = np.array([x_distance, y_distance, z_distance])

                distance = np.linalg.norm(distance_3d)

                # distance no further than cutoff radius:
                if 0 < distance <= self.SystemInfo.cutoff():
                    neighbours_distance.append(distance)
                    new_neighbours.append(index)

        # overwrite neighbours with the correct ones.
        neighbours = new_neighbours

        # Create namedtuple for easy access of output
        Result = collections.namedtuple("Neighbour_result", ["nb_ID", "nb_dist"])
        r = Result(nb_ID=neighbours, nb_dist=neighbours_distance)

        return r


    def _create_neighbours_frame(self):
        """
        Create a data frame -> Dictionary which contains the particle IDs for the neighbours
        and the distances.
        There are two dictionaries. One for the neighbour IDs and one for the distance.
        As key the number of the neighbour is used.
        """
        particle_number = self.SystemInfo.num_particles()
        self._neighbours_frame_IDs = {}
        self._neighbours_frame_dist = {}

        for i in range(particle_number):
            nb = self._neighbours_for_one(i)
            key = i
            # If it does not have neighbours there should be no key for it.
            if not nb:
                self._neighbours_frame_IDs[i] = nb.nb_ID
                self._neighbours_frame_dist[i] = nb.nb_dist
            else:
                # key for a particle does not exist till now
                if key not in self._neighbours_frame_IDs.keys():
                    self._neighbours_frame_IDs[i] = nb.nb_ID
                    self._neighbours_frame_dist[i] = nb.nb_dist
                # if some values already exist then add the new ones to them.
                else:
                    existing_IDs = self._neighbours_frame_IDs[i]
                    existing_dist = self._neighbours_frame_dist[i]
                    if type(existing_IDs) is int:
                        existing_IDs = [existing_IDs]
                        existing_dist = [existing_dist]

                    merged_IDs = existing_IDs + nb.nb_ID
                    merged_dist = existing_dist + nb.nb_dist

                    self._neighbours_frame_IDs[i] = merged_IDs
                    self._neighbours_frame_dist[i] = merged_dist

                # Already save the distances for both particles to avoid
                # calculating them twice.
                for count, nb_index in enumerate(nb.nb_ID):

                    if nb_index not in self._neighbours_frame_IDs.keys():
                        self._neighbours_frame_IDs[nb_index] = [i]
                        self._neighbours_frame_dist[nb_index] = [nb.nb_dist[count]]
                    else:
                        existing_IDs = self._neighbours_frame_IDs[nb_index]
                        existing_dist = self._neighbours_frame_dist[nb_index]

                        if type(existing_IDs) is int:
                            existing_IDs = [existing_IDs]
                            existing_dist = [existing_dist]

                        merged_IDs = existing_IDs + [i]
                        merged_dist = existing_dist + [nb.nb_dist[count]]

                        self._neighbours_frame_IDs[nb_index] = merged_IDs
                        self._neighbours_frame_dist[nb_index] = merged_dist

        pass

    def _get_neighbours_frame(self):
        """
        Call the whole frame that contains the neighbours for every particle and
        the distances. Only meant for testing purposes but can be changed to a public
        function if necessary.
        
        :return: dictionary
        """
        return {'IDs': self._neighbours_frame_IDs, 'Distance': self._neighbours_frame_dist}

    def get_neighbours(self, particle_ID):
        """
        This gets the neighbours of a single particle and the distances to
        its neighbours.
        
        :param particle_ID: particle ID in system
        
        :return: named tuple containing neighbours and distances
        """
        key = particle_ID
        if key in self._neighbours_frame_IDs.keys():
            neighbours = self._neighbours_frame_IDs[particle_ID]
            neighbours_distance = self._neighbours_frame_dist[particle_ID]

        Result = collections.namedtuple("Neighbour_result", ["nb_ID", "nb_dist"])
        r = Result(nb_ID=neighbours, nb_dist=neighbours_distance)

        return r

    def _get_neighbours_subcells(self, particle_pos):
        """
        Gets the subcell ID of the subcells which surround
        the subcell of the particle.
        To fulfill periodic boundary conditions, the subcell IDs
        are first calculated in 3D and subcell IDs which are
        out of bound are corrected.
        
        :param particle_pos: array with length 27
                             3d position of single particle
        
        :return: neighbours subcells
        """

        m = self._subcells_inrow  # makes code easier to read
        # initialize 3d subcell IDs with subcell of the particle
        subcells_id_3d = np.zeros((27, 3))
        subcells_id_3d[:] = self._3d_subcell_id(particle_pos)

        # First set of neighbour cells 0 to 8
        for cell in range(9):
            # x coordinates
            subcells_id_3d[cell][0] = math.floor((particle_pos[0]
                                                  - self._subcell_length)
                                                 / self._subcell_length)

        # cells 18 to 26
        for cell in range(18, 27):
            # x coordinate
            subcells_id_3d[cell][0] = math.floor((particle_pos[0]
                                                  + self._subcell_length)
                                                  / self._subcell_length)

        # y-coordinates:
        for cell in [0, 1, 2, 9, 10, 11, 18, 19, 20]:
            subcells_id_3d[cell][1] = self._cell_y(1, particle_pos)
        for cell in [6, 7, 8, 15, 16, 17, 24, 25, 26]:
            subcells_id_3d[cell][1] = self._cell_y(0, particle_pos)
        # z-coordinates:
        for cell in [0, 3, 6, 9, 12, 15, 18, 21, 24]:
            subcells_id_3d[cell][2] = self._cell_z(1, particle_pos)
        for cell in [2, 5, 8, 11, 14, 17, 20, 23, 26]:
            subcells_id_3d[cell][2] = self._cell_z(0, particle_pos)

        # initialize neighbour subcells (3x3x3 cube)
        neighbour_subcells = [0] * 3 ** 3

        # transform 3d subcell ID to an integer
        for cell in range(27):

            # check if subcell is out of bounds(<0 or bigger than boxsize)
            for index in range(3):
                if subcells_id_3d[cell][index] < 0:
                    subcells_id_3d[cell][index] = m - 1
                if subcells_id_3d[cell][index] > m - 1:
                    subcells_id_3d[cell][index] = 0

            subcell_id = subcells_id_3d[cell][0] \
                         + (subcells_id_3d[cell][1] * m) \
                         + (subcells_id_3d[cell][2] * (m ** 2))

            neighbour_subcells[cell] = int(subcell_id)

        return neighbour_subcells

# Following functions are for minor operations that occur several times.\n"
# Functions: _3d_subcell_id, _cell_y, _cell_z

    def _3d_subcell_id(self, particle_pos):
        """
        Create subcell ID in 3d for a particle
        
        :param particle_pos: 3d coordinates of single particle
        
        :return: 3d-subcell ID
        """
        subcell_id_3d = np.zeros(3)
        for axis in range(3):
            subcell_id_3d[axis] = math.floor(particle_pos[axis]
                                            / self._subcell_length)
        return subcell_id_3d

    def _cell_y(self, positive, particle_pos):
        """
        Calculates the subcell id for the y axis
        
        :param positive: boolean, if True the subcell id in positive
                        direction will be calculated
        :param particle_pos: 3d coordinates of single particle
        
        :return: subcell id for y axis
        """
        if positive == 0:
            y_id = math.floor((particle_pos[1] + self._subcell_length) / self._subcell_length)
        else:
            y_id = math.floor((particle_pos[1] - self._subcell_length) / self._subcell_length)
        return y_id

    def _cell_z(self, positive, particle_pos):
        """
        Calculates the subcell id for the y axis
        
        :param positive: boolean, if True the subcell id in positive
                         direction will be calculated
        :param particle_pos: 3d coordinates of a single particle
        
        :return: subcell id for y axis
        """
        if positive == 0:
            z_id = math.floor((particle_pos[2] + self._subcell_length) / self._subcell_length)
        else:
            z_id = math.floor((particle_pos[2] - self._subcell_length) / self._subcell_length)
        return z_id
