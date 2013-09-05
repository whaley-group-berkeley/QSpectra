import numpy as np


def tensor(*args):
    return reduce(np.kron, args)


def extend_vib_operator(n_vibrational_levels, m, vib_operator):
    """
    Extends the vibrational operator vib_operator, associated with
    vibrational mode m, into an operator on the full vibrational subspace
    """
    return tensor(np.eye(np.prod(n_vibrational_levels[0:m])),
                  vib_operator,
                  np.eye(np.prod(n_vibrational_levels[
                                     m+1:n_vibrational_levels.size])))


def vib_annihilate(N):
    """
    Returns the annihilation operator for a vibrational mode with N levels
    """
    return np.diag(np.sqrt(np.arange(1, N)), k=1)


def vib_create(N):
    """
    Returns the creation operator for a vibrational mode with N levels
    """
    return np.diag(np.sqrt(np.arange(1, N)), k=-1)


def unit_vec(n, N, dtype=complex):
    """
    Returns the unit vector in direction n in N dimensions.
    """
    v = np.zeros(N, dtype=dtype)
    v[n] = 1
    return v


def basis_transform(X, U):
    """
    Transform X, a state vector, operator, vectorized operator or super-
    operator, into the basis given by the unitary transformation matrix U

    How to apply the transformation is inferred by the dimensions of X and U.

    Reference
    ---------
    Havel, T. F. Robust procedures for converting among Lindblad, Kraus and
    matrix representations of quantum dynamical semigroups. J Math. Phys.
    44, 534-557 (2003).
    """
    N = len(U)
    if X.shape == (N,):
        # X is a vector in Hilbert space
        return U.T.conj().dot(X)
    elif X.shape == (N, N):
        # X is an operator
        return U.T.conj().dot(X).dot(U)
    elif X.shape[0] == N ** 2:
        # X is in Liouville space
        U_S = np.kron(U, U)
        if X.shape == (N ** 2,):
            # X is a vectorized operator
            return U_S.T.conj().dot(X)
        elif X.shape == (N ** 2, N ** 2):
            # X is a super-operator
            return U_S.T.conj().dot(X).dot(U_S)
    raise ValueError('basis transformation incompatible with '
                     'operator dimensions')


def all_states(N, subspace='gef'):
    """
    List all states in the desired subspace for N pigments

    Assumes hard-core bosons (no double-excitations of the same state)

    Parameters
    ----------
    N : int
        Number of sites.
    subspace : container, default 'gef'
        Container of any or all of 'g', 'e' and 'f' indicating the desired
        subspaces on which the operator is defined.

    Returns
    -------
    states : list
        List of all states defined in the desired subspace, where each state is
        defined as a list of sites in the excited state
    """
    states = []
    if 'g' in subspace:
        states.append([])
    if 'e' in subspace:
        for i in xrange(N):
            states.append([i])
    if 'f' in subspace:
        for i in xrange(N):
            for j in xrange(i + 1, N):
                states.append([i, j])
    return states


def operator_1_to_2(operator1):
    """
    From the matrix representation of an operator in the 1-excitation subspace,
    determine its representation in the 2-excitation subspace

    Assumes that given the matrix element A_{nm}, the full representation of
    the operator is given by:
        \sum_{n,m} A_{nm} a^\dagger_n a_m

    Parameters
    ----------
    operator1 : np.ndarray
        Matrix representation of an operator defined on the 1-excitation
        subspace

    Returns
    -------
    operator2 : np.ndarray
        Matrix representation of the operator defined on the 2-excitation
        subspace
    """
    states = all_states(len(operator1), 'f')
    operator2 = np.zeros((len(states), len(states)), dtype=operator1.dtype)

    def delta(i, j):
        return int(i == j)

    for m in xrange(len(states)):
        for n in xrange(len(states)):
            (i, j), (k, l) = states[m], states[n]
            operator2[m, n] = (operator1[j, l] * delta(i, k) +
                               operator1[j, k] * delta(i, l) +
                               operator1[i, l] * delta(j, k) +
                               operator1[i, k] * delta(j, l))
    return operator2


def operator_extend(operator1, subspace='gef'):
    """
    Extend an operator defined in the 1-excitation subspace to include the
    ground and/or double-excitation subspaces

    Assumes that given the matrix element A_{nm}, the full representation of
    the operator is given by:
        \sum_{n,m} A_{nm} a^\dagger_n a_m

    Parameters
    ----------
    operator1 : np.ndarray
        Matrix representation of an operator defined on the 1-excitation
        subspace
    subspace : container, default 'gef'
        Container of any or all of 'g', 'e' and 'f' indicating the desired
        subspaces on which the operator is defined.

    Returns
    -------
    out : np.ndarray
        Matrix representation of the operator defined on the requested subspace
    """
    operators = []
    if 'g' in subspace:
        operators.append(np.array([[0]]))
    if 'e' in subspace:
        operators.append(operator1)
    if 'f' in subspace:
        operators.append(operator_1_to_2(operator1))

    sizes = [len(op) for op in operators]
    overall_size = sum(sizes)
    operator_extended = np.zeros((overall_size, overall_size),
                                 dtype=operator1.dtype)
    starts = np.cumsum([0] + sizes[:-1])
    ends = np.cumsum(sizes)
    for start, end, op in zip(starts, ends, operators):
        operator_extended[start:end, start:end] = op
    return operator_extended


def transition_operator(n, n_sites, subspace='gef', include_transitions='-+'):
    """
    Calculate the transition operator for creating an removing an excitation
    at site n of n_sites overall

    Parameters
    ----------
    n : int
        Site at which to alter the number of excitations (0-indexed).
    n_sites : int
        Number of sites.
    subspace : container, default 'gef'
        Container of any or all of 'g', 'e' and 'f' indicating the desired
        subspaces on which the operator is defined.
    include_transitions : str, default '-+'
        String containing '-' and/or '+' to indicating whether or not to
        annihilation and/or creation of an excitation.

    Returns
    -------
    out : np.ndarray
        Transition operator in matrix form
    """
    states = all_states(n_sites, subspace)
    dipole_matrix = np.zeros((len(states), len(states)))
    for i in xrange(len(states)):
        for j in xrange(len(states)):
            if (('+' in include_transitions and
                 states[i] == sorted(states[j] + [n]))
                or ('-' in include_transitions and
                    sorted(states[i] + [n]) == states[j])):
                dipole_matrix[i, j] = 1
    return dipole_matrix


class SubspaceError(Exception):
    """
    Error class to indicate an invalid subspace
    """


def n_excitations(n_sites=1, n_vibrational_states=1):
    """
    Given the number of sites and vibrational states, returns the number of 0-,
    1- and 2-excitation states as a three item array
    """
    n_exc = np.array([1, n_sites, int(n_sites * (n_sites - 1) / 2)])
    return n_exc * n_vibrational_states


def extract_subspace(subspaces_string):
    """
    Given a string a subspace in Liouville space or a mapping between subspaces,
    returns the minimal containing Hilbert space subspace
    """
    return set(subspaces_string) - {',', '-', '>'}


def hilbert_subspace_index(subspace, all_subspaces, n_sites,
                           n_vibrational_states=1):
    """
    Given a Hilbert subspace 'g', 'e' or 'f' and the set of all subspaces on
    which a state is defined, returns a slice object to select all elements in
    the given subspace

    Examples
    --------
    >>> hilbert_subspace_index('g', 'gef', 2)
    slice(0, 1)
    >>> hilbert_subspace_index('e', 'gef', 2)
    slice(1, 3)
    >>> hilbert_subspace_index('f', 'gef', 2)
    slice(3, 4)
    """
    n_exc = n_excitations(n_sites, n_vibrational_states)
    included_n_exc = ['gef'.index(s) for s in all_subspaces]
    breaks = [0] + list(np.cumsum(n_exc[included_n_exc]))
    if subspace in all_subspaces:
        N = all_subspaces.index(subspace)
        return slice(breaks[N], breaks[N + 1])
    else:
        raise SubspaceError("{} not in set of all subspaces '{}'".format(
                            subspace, all_subspaces))
