# This is a simple exploratory script applying UMAP to the features
# in the all-codes dataset and the code groups dataset, to visualise
# any correlations between the reduction and the bleeding outcome,
# or other feature groups of interest.
#
# The hypothesis is that, if there are any patterns in the bleeding
# outcome in the reduced-dimension version of the all codes dataset,
# then it might be useful as a preprocessor step in building models
# for bleeding.

import save_datasets as ds
import umap
import matplotlib.pyplot as plt
import seaborn as sns

# Read the datasets with the code-group predictors and the all-codes
# predictors. You will need to pick these interactively
df_code_groups = ds.load_dataset_interactive("hes_code_groups_dataset")
df_all_codes = ds.load_dataset_interactive("hes_all_codes_dataset")

print(df_code_groups.columns)
exit()

# Need these two to be in sync; i.e. they need the same number
# of rows, consistently indexed by idx_episode_id
if df_code_groups.shape[0] != df_all_codes.shape[0]:
    raise RuntimeError("Incompatible datasets (different rows); rerun hes_episodes.py")

# Reduce the dataset size for now
n = 5000
index = df_code_groups.index[0:n]
df_code_groups = df_code_groups[df_code_groups.index.isin(index)]
df_all_codes = df_all_codes[df_all_codes.index.isin(index)]

# Get the bleeding outcome
bleeding_outcome = df_all_codes["bleeding_al_ani_outcome"]

df_to_reduce = df_all_codes.filter(regex="(diagnosis|procedure)")
print(df_to_reduce)

# UMAP has the following parameters:
#
# - n_neighbors: this is the number of nearest neighbors to
#   use in the approximation of a uniform distance around
#   each data point in the original manifold. Choosing a
#   a large number will course-grain the manifold, so that
#   the uniform distances are approximated over larger groups
#   of spells.
# - min_dist: in the dimension-reduced manifold (after projection
#   from the original manifold), the local-connectedness condition
#   which translated to assuming that each data point is 0 distance
#   away from its nearest neighbour, must translate to an arbitrary
#   choice for what this minimum distance is in the Euclidean plane.
#   Making it small will cause more clustering, whereas making it
#   large will push points away from each other, which may focus
#   more on the overall topological structure.
# - n_components: the n here is the dimension of the reduced space,
#   which is the manifold R^n with the standard topology arising
#   from Eucliean distances
# - metric: which metric is used to measure distance between the
#   different points of the dataset in the original (ambient)
#   space R^m (m is the number of columns in the original dataset).
#   Here, there is one binary column per clinical code, and two rows
#   (spells) are considered different according to how many of their
#   clinical codes differ -- this is the Hamming distance.

mapper = umap.UMAP(metric="hamming", random_state=1, verbose=True)
embedding = mapper.fit_transform(df_to_reduce)

plt.scatter(
    embedding[:, 0],
    embedding[:, 1],
    c=[sns.color_palette()[x] for x in bleeding_outcome],
)
plt.gca().set_aspect("equal", "datalim")
plt.title("UMAP projection with bleeding distribution", fontsize=24)
plt.show()
