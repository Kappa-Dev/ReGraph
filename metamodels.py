from regraph.library.data_structures import TypedDiGraph


base_metamodel = TypedDiGraph()

base_metamodel.add_nodes_from(
    [
        ("agent", ""),
        ("action", "")
    ]
)
base_metamodel.add_edges_from(
    [
        ("agent", "agent"),
        ("agent", "action"),
        ("action", "action"),
        ("action", "agent"),
    ]
)

metamodel_AG = TypedDiGraph(base_metamodel)

metamodel_AG.add_nodes_from(
    [
        ("protein", "agent"),
        ("region", "agent"),
        ("residue", "agent"),
        ("family", "agent"),
        ("complex", "agent"),
        ("small_molecule", "agent"),
        ("state", "agent"),

        ("FAM", "action"),
        ("FAM_s", "action"),
        ("FAM_t", "action"),

        ("BND", "action"),
        ("BND_s", "action"),

        ("BRK", "action"),
        ("BRK_t", "action"),

        ("MOD", "action"),
        ("MOD_s", "action"),
        ("MOD_t", "action")
    ])

metamodel_AG.add_edges_from(
    [
        ("protein", "complex"),
        ("residue", "complex"),
        ("small_molecule", "complex"),
        ("family", "complex"),
        ("complex", "complex"),

        ("region", "protein"),
        ("residue", "protein"),

        ("residue", "region"),
        ("residue", "family"),

        ("state", "protein"),
        ("state", "region"),
        ("state", "residue"),
        ("state", "family"),
        ("state", "complex"),
        ("state", "small_molecule"),

        ("BND_s", "BND"),
        ("protein", "BND_s"),
        ("region", "BND_s"),
        ("small_molecule", "BND_s"),
        ("family", "BND_s"),
        ("complex", "BND_s"),

        ("BRK", "BND"),
        ("BRK_t", "BRK"),
        ("BRK_t", "protein"),
        ("BRK_t", "region"),
        ("BRK_t", "family"),
        ("BRK_t", "complex"),
        ("BRK_t", "small_molecule"),

        ("MOD_s", "MOD"),
        ("MOD_t", "MOD"),
        ("protein", "MOD_s"),
        ("region", "MOD_s"),
        ("family", "MOD_s"),
        ("complex", "MOD_s"),
        ("small_molecule", "MOD_s"),
        ("MOD_t", "state"),

        ("FAM_s", "FAM"),
        ("FAM_t", "FAM"),
        ("protein", "FAM_s"),
        ("region", "FAM_s"),
        ("small_molecule", "FAM_s"),
        ("family", "FAM_s"),
        ("complex", "FAM_s"),
        ("FAM_t", "family"),
    ]
)

metamodel_kappa = TypedDiGraph(base_metamodel)

metamodel_kappa.add_nodes_from([
    ('agent', 'agent'),
    ('site', 'agent'),
    ('state', 'agent'),
    ('BND', 'action'),
    ('BRK', 'action'),
    ('MOD', 'action'),
    ('is_BND', 'action'),
    ('s_BND', 'action'),
    ('t_BRK', 'action'),
    ('t_MOD', 'action'),
    ('SYN/DEG', 'action'),
    ('s_SD', 'action'),
    ('t_SD', 'action'),
    ('is_FREE', 'action'),
    ('t_FREE', 'action'),
    ('not_BND', 'action'),
])

metamodel_kappa.add_edges_from([
    ('site', 'agent'),
    ('state', 'site'),
    ('site', 's_BND'),
    ('s_BND', 'BND'),
    ('s_BND', 'is_BND'),
    ('s_BND', 'not_BND'),
    ('t_BRK', 'BRK'),
    ('t_BRK', 'site'),
    ('t_MOD', 'MOD'),
    ('t_MOD', 'state'),
    ('s_SD', 'SYN/DEG'),
    ('t_SD', 'SYN/DEG'),
    ('agent', 's_SD'),
    ('t_SD', 'agent'),
    ('t_FREE', 'is_FREE'),
    ('t_FREE', 'site'),
])

base_kami = TypedDiGraph()
base_kami.add_nodes_from(
    [
        ("component", ""),
        ("test", ""),
        ("state", ""),
        ("action", "")
    ]
)

base_kami.add_edges_from(
    [
        ("component", "component"),
        ("state", "component"),
        ("component", "action"),
        ("action", "component"),
        ("component", "test"),
        ("action", "state")
    ]
)

kami = TypedDiGraph(base_kami)

kami.add_nodes_from(
    [
        ("agent", "component"),
        ("region", "component"),
        ("residue", "component"),
        ("locus", "component"),
        ("state", "state"),
        ("mod", "action"),
        ("syn", "action"),
        ("deg", "action"),
        ("bnd", "action"),
        ("brk", "action"),
        ("is_bnd", "test"),
        ("is_free", "test")


    ]
)

kami.add_edges_from(
    [
        ("region", "agent"),
        ("residue", "agent"),
        ("state", "agent"),
        ("syn", "agent"),
        ("deg", "agent"),
        ("state", "region"),
        ("state", "residue"),
        ("locus", "agent"),
        ("locus", "region"),
        ("mod", "state"),
        ("locus", "bnd"),
        ("locus", "brk"),
        ("locus", "is_bnd"),
        ("locus", "is_free")
    ]
)

for n in kami.nodes():
    kami.node[n].attributes_typing = lambda _: True
for n in metamodel_kappa.nodes():
    metamodel_kappa.node[n].attributes_typing = lambda _: True
