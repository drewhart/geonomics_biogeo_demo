#!/usr/bin/python
# IBD_IBE_test.py

# import geonomics
import geonomics as gnx

# other imports
from copy import deepcopy
# from itertools import chain
import numpy as np
from sklearn.decomposition import PCA
# import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib import gridspec
from mpl_toolkits.mplot3d import Axes3D
import os
import time
import statsmodels.api as sm

# set some plotting params
img_dir = ('/home/drew/Desktop/stuff/berk/research/projects/sim/methods_paper/'
           'img/final/')
ax_fontdict = {'fontsize': 12,
               'name': 'Bitstream Vera Sans'}
ttl_fontdict = {'fontsize': 15,
                'name': 'Bitstream Vera Sans'}
mark_size = 15


# function for running and plotting genetic PCA
def plot_genetic_PCA(species, land):
    # get array of resulting genomic data (i.e. 'speciome'),
    # genotypes meaned by individual
    speciome = np.mean(np.stack([i.g for i in species.values()]), axis=2)
    # run PCA on speciome
    pca = PCA(n_components=3)
    PCs = pca.fit_transform(speciome)
    # normalize the PC results
    norm_PCs = (PCs - np.min(PCs,
                             axis=0)) / (np.max(PCs,
                                                axis=0) - np.min(PCs,
                                                                 axis=0))
    # use first 3 PCs to get normalized values for R, G, & B colors
    PC_colors = norm_PCs * 255
    # scatter all individuals on top of landscape, colored by the
    # RBG colors developed from the first 3 geonmic PCs
    xs = mod.comm[0]._get_xs()
    ys = mod.comm[0]._get_ys()
    # get environmental raster, with barrier masked out
    masked_env = deepcopy(mod.land[0].rast)
    masked_env[mod.land[1].rast == 0] = np.nan
    # create light colormap for plotting landscape
    # bot = plt.cm.get_cmap('Blues', 256)(np.linspace(0.4, 0.45, 2))[0]
    # top = plt.cm.get_cmap('Reds', 256)(np.linspace(0.4, 0.45, 2))[0]
    # cols = np.vstack((top, bot))
    # cmap = mpl.colors.ListedColormap(cols, name='OrangeBlue')
    cmap = plt.cm.RdBu_r
    cmap.set_bad(color='#8C8C8C')
    # plot landscape
    # plt.imshow(masked_env, cmap=cmap, alpha=0.8)
    plt.pcolormesh(land._x_cell_bds, land._y_cell_bds, masked_env, cmap=cmap)
    # scatter plot of individuals, colored by composite PC score
    plt.scatter(xs, ys, c=PC_colors/255.0, s=mark_size, edgecolors='black')
    # fix x and y limits
    [f([dim - 0.5 for dim in (0, mod.land.dim[0])]) for f in (plt.xlim,
                                                              plt.ylim)]
    # get rid of x and y ticks
    [f([]) for f in (plt.xticks, plt.yticks)]


# calculate euclidean distance from two n-length vectors
def calc_euc(x, y):
    euc = np.sqrt(sum([(n-m)**2 for n, m in zip(x, y)]))
    return euc


# calculate lower-triangular of PCA-bsaed Euclidean genetic distances between
# all individuals, using a 'speciome' (2d array of all individs' genomes)
def calc_dists(species, dist_type='gen', env_lyrs=None, return_flat=True):
    # calculate genetic distance as the euclidean distance between individuals
    # in genetic PC space
    if dist_type == 'gen':
        speciome = np.mean(np.stack([i.g for i in species.values()]), axis=2)
        pca = PCA()
        vals = pca.fit_transform(speciome)
    # calculate geographic distance as the linear euclidean distance between
    # individuals
    elif dist_type == 'geo':
        vals = np.stack([np.array((i.x, i.y)) for i in species.values()])
    # calculate environmental distance as the euclidean distance between
    # individuals' environments, for all environmental layers specified by
    # the 'env_lyrs' argument
    elif dist_type == 'env':
        vals = np.stack([np.array(i.e)[env_lyrs] for i in species.values()])
    # print(vals)
    # print(vals.shape)
    n_ind = vals.shape[0]
    dist_mat = np.ones([n_ind] * 2) * -999
    # dist_vals = [[calc_euc(i, j) for j in vals[n:,
    #                                        :]] for n, i in enumerate(vals)]
    for i in range(n_ind):
        for j in range(0, i+1):
            dist_mat[i, j] = calc_euc(vals[i, :], vals[j, :])
    # check that all diagonal values are 0
    assert np.all(np.diag(dist_mat) == 0), "Not all diagonal values are 0!"

    if return_flat:
        # flatten the lower triangle, if return 1-d of values
        dists = dist_mat[np.tril_indices(dist_mat.shape[0], -1)]
        assert dists.size == (n_ind**2 - n_ind)/2, ("Length not equal "
                                                    "to n(n-1)/2!")
    else:
        # make it a symmetric dist matrix, if returning the matrix
        dist_mat[dist_mat == -999] = 0
        dists = dist_mat + dist_mat.T
        assert dists.size == n_ind**2, "Size not equal to n*n!"
    # dist_vals = [item[1:] for item in dist_vals]
    # dists = [*chain.from_iterable(dist_vals)]
    # assert that the length is correct
    return dists


# make empty figure
fig = plt.figure(figsize=(6.75, 9.25))
gs = gridspec.GridSpec(4, 2,
                       width_ratios=[1, 1.4],
                       height_ratios=[1, 1, 0.05, 0.5])
# start timer
start = time.time()

# make model
mod = gnx.make_model('./geonomics/examples/IBD_IBE/IBD_IBE_params.py')

# define number of timesteps
T = 1000

# burn model in
mod.walk(20000, 'burn')

# plot genetic PCA before evolution begins
# ax1 = fig.add_subplot(321)
ax1 = plt.subplot(gs[0])
#ax1.set_title('t = 0')
plot_genetic_PCA(mod.comm[0], mod.land)
ax1.set_ylabel('before evolution')

# plot phenotypes before evolution begins
# ax3 = fig.add_subplot(323)
ax2 = plt.subplot(gs[1])
mask = np.ma.masked_where(mod.land[1].rast == 0, mod.land[1].rast)
mod.plot_phenotype(0, 0, mask_rast=mask, size=mark_size, cbar='force')
[f((-0.5, 39.5)) for f in [plt.xlim, plt.ylim]]

# run model for T timesteps
mod.walk(T)

# finish timer
stop = time.time()
tot_time = stop - start

# plot genetic PCA after 1/4T timesteps
# ax2 = fig.add_subplot(322)
ax3 = plt.subplot(gs[2])
#ax3.set_title('t = %i' % T)
plot_genetic_PCA(mod.comm[0], mod.land)
ax3.set_ylabel('after evolution')

# plot the individuals' phenotypes
# ax4 = fig.add_subplot(324)
ax4 = plt.subplot(gs[3])
mod.plot_phenotype(0, 0, mask_rast=mask, size=mark_size, cbar='force')
[f((-0.5, 39.5)) for f in [plt.xlim, plt.ylim]]

# plot IBD and IBE
spp_subset = {ind: mod.comm[0][ind] for ind in np.random.choice([*mod.comm[0]],
                                                                100)}
gen_dists = calc_dists(spp_subset)
scaled_gen_dists = gen_dists/gen_dists.max()
assert (np.all(scaled_gen_dists >= 0)
        and np.all(scaled_gen_dists <= 1)), ('Scaled genetic dist is outside '
                                             '0 and 1!')
geo_dists = calc_dists(spp_subset, 'geo')
env_dists = calc_dists(spp_subset, 'env', [0])
# ax5 = fig.add_subplot(325)
ax5 = plt.subplot(gs[6])


# create 3d axes, and label for geo, env, and gen
fig3d = plt.figure()
ax3d = fig3d.add_subplot(111, projection='3d')
# get 3d-scatter colors
col3d = ((geo_dists / geo_dists.max()) + (env_dists / env_dists.max())) / 2
# scatter all 3 vars on those axes
ax3d.scatter(geo_dists, env_dists, scaled_gen_dists, alpha=0.5, c=col3d,
             cmap='plasma')
ax3d.set_xlabel('geo', size=15)
ax3d.set_ylabel('env', size=15)
ax3d.set_zlabel('gen', size=15)
# run multiple linear regression of gen on geo and env dists
# mlr_est = sm.GLM(np.array(scaled_gen_dists.T),
#                 np.vstack((geo_dists, env_dists)).T,
#                 family=sm.families.Binomial(sm.families.links.cloglog)).fit()
mlr_est = sm.Logit(endog=np.array(scaled_gen_dists.T),
                   exog=np.vstack((geo_dists, env_dists)).T).fit()
# create predicted surface, and add to 3d plot
y_vals = np.arange(0, 1.01, 0.01)
ys = np.hstack([list(y_vals) for _ in range(len(y_vals))])
xs = np.hstack([[n] * len(y_vals) for n in np.linspace(0, 50, len(y_vals))])
zs = mlr_est.predict(np.vstack((xs, ys)).T)
xs = xs.reshape([len(y_vals)] * 2)
ys = ys.reshape([len(y_vals)] * 2)
zs = zs.reshape([len(y_vals)] * 2)
# surf_cols = ((xs / xs.max()) + (ys / ys.max())) / 2
# surf_cols = np.int64(surf_cols * 255) + 1
# ax3d.plot_surface(xs, ys, zs, facecolors=surf_cols, alpha=0.5, cmap='plasma')
ax3d.plot_surface(xs, ys, zs, color='black', alpha=0.4)


plt.scatter(geo_dists, scaled_gen_dists, alpha=0.05, c='black')
# plt.scatter(geo_dists, gen_dists, alpha=0.05, c='black')
# add a regression line (NOTE: doesn't include an intercept by default,
# so I need to include one manually in the design matrix)
# est = sm.GLM(np.array(scaled_gen_dists).T,
#             geo_dists.T,
#             family=sm.families.Binomial(sm.families.links.cloglog)).fit()
# est = sm.OLS(np.array(gen_dists).T,
#             np.array(([1] * len(geo_dists), geo_dists)).T).fit()
x_preds = np.arange(0, 50.1, 0.1)
y_preds = np.linspace(0, 1, len(x_preds))
z_preds = mlr_est.predict(np.vstack((x_preds, y_preds)).T)
# y_preds = est.predict(np.vstack(([1] * len(x_preds), x_preds)).T)
plt.plot(x_preds, z_preds, color='#C33B3B')
plt.text(min(geo_dists) + 0.6 * (max(geo_dists) - min(geo_dists)),
         0.2, 'slope:    %0.4f' % mlr_est.params[0],
         color='#C33B3B', size=9)
p_val_lt = mlr_est.pvalues[0] < 0.001
assert p_val_lt, 'p-value not less than 0.001!'
plt.text(min(geo_dists) + 0.6 * (max(geo_dists) - min(geo_dists)),
         0.05, 'p-value < 0.001',
         color='#C33B3B', size=9)
plt.text(min(geo_dists) + 0.6 * (max(geo_dists) - min(geo_dists)),
         0.45, 'Pseudo-$R^{2}$:   %0.4f' % mlr_est.prsquared,
         color='#C33B3B', size=9)
ax5.set_title('IBD')
ax5.set_xlabel('geographic distance')
ax5.set_ylabel('rescaled genetic distance')
# ax5.set_ylim(int(np.floor(min(gen_dists))), int(np.ceil(max(gen_dists))))
ax5.set_ylim((0, 1))
# ax5.set_aspect('equal')
# ax6 = fig.add_subplot(326, sharey=ax5)
ax6 = plt.subplot(gs[7], sharey=ax5)
plt.scatter(env_dists, scaled_gen_dists, alpha=0.05, c='black')
# plt.scatter(env_dists, gen_dists, alpha=0.05, c='black')
# add a regression line (a quadratic regression, to allow for a saturating
# pattern within the range of x values)
# est = sm.GLM(np.array(scaled_gen_dists).T,
#             env_dists.T,
#             family=sm.families.Binomial(sm.families.links.cloglog)).fit()
#est = sm.OLS(np.array(gen_dists).T,
#             np.array(([1] * len(env_dists), env_dists)).T).fit()
# x_preds = np.arange(0, 1, 0.01)
# z_preds = est.predict(x_preds.T)
# y_preds = est.predict(np.vstack(([1] * len(x_preds), x_preds)).T)
plt.plot(y_preds, z_preds, color='#C33B3B')
plt.text(min(env_dists) + 0.6 * (max(env_dists) - min(env_dists)),
         0.2, 'slope:    %0.3f' % mlr_est.params[0],
         color='#C33B3B', size=9)
p_val_lt = mlr_est.pvalues[0] < 0.001
assert p_val_lt, 'p-value not less than 0.001!'
plt.text(min(env_dists) + 0.6 * (max(env_dists) - min(env_dists)),
         0.05, 'p-value < 0.001',
         color='#C33B3B', size=9)
plt.text(min(geo_dists) + 0.6 * (max(geo_dists) - min(geo_dists)),
         0.45, 'Pseudo-$R^{2}$:   %0.4f' % mlr_est.prsquared,
         color='#C33B3B', size=9)
ax6.set_title('IBE')
ax6.set_xlabel('environmental distance')
ax6.set_yticks([])
# ax6.set_ylabel('genetic distance')
# ax6.set_aspect('equal')

# TODO: add regression line to each plot
fig.tight_layout()
plt.subplots_adjust(left=0.05, bottom=0.07, right=0.98, top=0.96, wspace=0.07,
                    hspace=0.16)
plt.show()
plt.savefig(os.path.join(img_dir, 'IBD_IBE.pdf'), format='pdf', dpi=1000)

# print out time
print("\n\nModel ran in %0.2f seconds." % tot_time)
