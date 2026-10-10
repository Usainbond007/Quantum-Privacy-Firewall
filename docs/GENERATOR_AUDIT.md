# Generator audit (Table I, 47 generators)

The paper names the generators but does not define them; every generator is our interpretation. The tier says how much of each is actually verified by `tests/test_generator_audit.py` and `tests/test_paper_circuits.py`:

- **semantic**: a mathematical invariant is checked (statevector, truth table / classical reference, stabilizers, analytic probability, Bernstein-Vazirani recovery).
- **structural**: gate content and qubit topology are checked against the named construction; the dynamics/semantics are NOT checked.
- **analogue**: only normalisation, exact width and determinism are checked; the circuit is a structural stand-in for its name.

Totals: 24 semantic, 20 structural, 3 analogue (of 47).

| class | generator | tier |
|---|---|---|
| entanglement_generation | ghz | semantic |
| entanglement_generation | bell_chain | structural |
| entanglement_generation | graph_line | semantic |
| entanglement_generation | graph_ring | semantic |
| entanglement_generation | graph_star | semantic |
| entanglement_generation | w_state_ladder | semantic |
| entanglement_generation | cluster_grid | semantic |
| fourier_like | qft_swaps | semantic |
| fourier_like | qft_no_swaps | semantic |
| fourier_like | iqft_swaps | semantic |
| fourier_like | iqft_no_swaps | semantic |
| fourier_like | approx_qft | analogue |
| fourier_like | phase_estimation | semantic |
| fourier_like | qft_phase_gradient | analogue |
| phase_oracle_like | parity | semantic |
| phase_oracle_like | parity_odd | semantic |
| phase_oracle_like | parity_even | semantic |
| phase_oracle_like | phase_oracle | structural |
| phase_oracle_like | phase_ladder | structural |
| phase_oracle_like | controlled_phase_ladder | structural |
| phase_oracle_like | diagonal_phase_pattern | structural |
| amplitude_amplification | grover | semantic |
| amplitude_amplification | grover_zero | semantic |
| amplitude_amplification | grover_two_iterations | semantic |
| amplitude_amplification | parity_amplitude_amplification | semantic |
| amplitude_amplification | fixed_point_amplitude_amplification | structural |
| amplitude_amplification | amplitude_estimation_style | analogue |
| variational_ansatz | hea_linear | structural |
| variational_ansatz | hea_ring | structural |
| variational_ansatz | hea_brickwork | structural |
| variational_ansatz | real_amplitudes | structural |
| variational_ansatz | twolocal_rx_rz | structural |
| variational_ansatz | qaoa_line | structural |
| variational_ansatz | qaoa_ring | structural |
| hamiltonian_simulation | trotter_zz_xx | structural |
| hamiltonian_simulation | trotter_zz_xx_ring | structural |
| hamiltonian_simulation | trotter_tfim | structural |
| hamiltonian_simulation | trotter_xxz | structural |
| hamiltonian_simulation | trotter_heisenberg | structural |
| hamiltonian_simulation | trotter_longitudinal_ising | structural |
| arithmetic_permutation | ripple_adder | semantic |
| arithmetic_permutation | incrementer | semantic |
| arithmetic_permutation | permutation_swaps | semantic |
| arithmetic_permutation | controlled_swap_network | structural |
| arithmetic_permutation | comparator | semantic |
| arithmetic_permutation | majority_logic | semantic |
| arithmetic_permutation | toffoli | semantic |

Bugs found by this audit and fixed: `incrementer` (ancillas randomly initialised), `comparator` (carry uncompute not the inverse), `parity_amplitude_amplification` (phase-kickback ancilla prepared in |+> instead of |->, so the oracle was a no-op).
