def hill_climb():
    K = 150
    k = int(K / 2)
    EWMA_alpha = 0.5
    epsilon = 1e-6  # Small constant to avoid division by zero

    winner_sets = []
    all_cost_curves = []
    all_edge_curves = []
    all_newly_infected_counts = []
    all_newly_infected_frac = []
    all_state_vectors = []

    for i in range(num_simulations):
        print("Simulation: ", i)

        # Fresh networks for each simulation
        contact_network = deepcopy(initial_contact)
        social_network = deepcopy(initial_social)

        # Randomly initialized utilities
        utilities = {node: random.uniform(0, 1) for node in contact_network.nodes()}

        # Randomly initialize K many seeds
        seed_vec = np.array([1 if node in random.sample(list(contact_network.nodes()), K) else 0 for node in contact_network.nodes()])
        prev_seed_vec = seed_vec.copy()

        cost_lst = []
        states_at_time = None
        prev_state_dict = None
        live_edge_at_time = None
        edge_counts = []
        last_batch_cost = None
        newly_infected_at_time = []
        newly_infected_frac_per_sim = []

        for t_cur in range(T):
            seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]

            simulation_results = SIR.Simulate_SIR(
                contact_network=contact_network, social_network=social_network,
                # Stepwise simulation: t=0 => no information spread beyond the current seeds
                T=0,
                beta=beta, gamma=gamma, mu=mu, init=init,
                # Quarantine mode: quarantine until recovery
                q=q,
                adherence=adherence,
                # Start quarantine immediately
                begin_q=0,
                # seeds=list(set(seed_set).union(cur_informed)),
                seeds=seed_set,
                # States from end of last step
                initial_state_dict=prev_state_dict
            )

            # Reset contact so initial connections are always known (but may be removed by quarantine)
            contact_network = deepcopy(initial_contact)
            # List of dictionaries
            sirs_states = simulation_results[4]
            # Dictionary from node to state at the end of this time step, to be fed into next step
            prev_state_dict = sirs_states[-1]
            # List of state dicts over time
            states_at_time = sirs_states if states_at_time is None else states_at_time + sirs_states

            # Current new infections this step
            current_new_i = given_at_time(t_cur, states_at_time, contact_network)
            newly_infected_at_time.append(current_new_i)
            newly_infected_frac_per_sim.append(current_new_i / n)

            # Live edges this step
            graph_vec = simulation_results[10]
            live_edges = [list(edge_set) for edge_set in graph_vec]

            # Update time-series of live edges
            live_edge_at_time = live_edges if live_edge_at_time is None else live_edge_at_time + live_edges
            edge_counts.append(len(live_edges[-1]))

            # At batch boundary: compute cost, update utilities, flip seeds
            if (t_cur + 1) % batch_interval == 0 or t_cur == T - 1:
                cost, _ = global_cost_function(newly_infected_at_time, live_edge_at_time, len(seed_set), t_cur)
                cost_lst.append(cost)

                # Stability-weighted utility update for active seeds
                num_active = max(sum(seed_vec), 1)
                hamming_dist = max(np.sum(seed_vec != prev_seed_vec), 1)

                for node in contact_network.nodes():
                    if seed_vec[node] == 1:
                        if last_batch_cost is None:
                            delta = 0.0
                        else:
                            delta = (cost - last_batch_cost) / (hamming_dist * num_active)

                        utilities[node] = EWMA_alpha * delta + (1 - EWMA_alpha) * utilities[node]

                last_batch_cost = cost

                # Save current seed vec before flipping
                prev_seed_vec = seed_vec.copy()

                # Flip phase with revised probabilities (size-preserving)
                flip_bound = random.randint(1, k)
                for _ in range(flip_bound):
                    node = random.choice(list(contact_network.nodes()))
                    g = utilities[node]
                    if seed_vec[node] == 0:
                        flip_prob = 1.0 / (g + epsilon)
                        flip_prob = min(flip_prob, 1.0)
                        if random.random() < flip_prob:
                            # Flip this node ON, flip a random current seed OFF
                            current_seeds = [n for n in contact_network.nodes() if seed_vec[n] == 1]
                            if current_seeds:
                                drop_node = random.choice(current_seeds)
                                seed_vec[node] = 1
                                seed_vec[drop_node] = 0
                    else:
                        flip_prob = 1.0 - 1.0 / (g + epsilon)
                        flip_prob = max(flip_prob, 0.0)
                        if random.random() < flip_prob:
                            # Flip this node OFF, flip a random non-seed ON
                            non_seeds = [n for n in contact_network.nodes() if seed_vec[n] == 0]
                            if non_seeds:
                                add_node = random.choice(non_seeds)
                                seed_vec[node] = 0
                                seed_vec[add_node] = 1

        final_seed_set = [node for node in contact_network.nodes() if seed_vec[node] == 1]

        winner_sets.append(final_seed_set)
        all_cost_curves.append(cost_lst)
        all_edge_curves.append(edge_counts)
        all_newly_infected_counts.append(newly_infected_at_time)
        all_newly_infected_frac.append(newly_infected_frac_per_sim)
        all_state_vectors.append(states_at_time)

    seed_set_counts = Counter(tuple(seed_set) for seed_set in winner_sets)
    most_common_seed_set = seed_set_counts.most_common(1)[0][0]

    return most_common_seed_set, all_cost_curves, all_edge_curves, all_newly_infected_counts, all_newly_infected_frac, all_state_vectors