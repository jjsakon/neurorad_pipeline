from __future__ import print_function

import os
import os.path as osp
from subprocess import call
from submission.log import logger
from numpy import savetxt
import pandas as pd
import nibabel as nb


def brainshift_correct(loc, sub, outfolder, fsfolder, overwrite=False):
    """ Corrects for brain shift using sequential quadratic
    programming optimization in R (package nloptr).
    :param loc: localization structure
    :param sub: subject name
    :param outfolder: where will logs and csv file be saved
    :param fsfolder: fresurfer folder for this subject
    :param overwrite: force processing and overwrite existing files
    """
    here = osp.realpath(osp.dirname(__file__))
    Rcorrection = osp.join(here, "brainshift", "duralDykstra.R")
    # sub = 'R1238N'
    # outfolder = '/data10/RAM/subjects/R1238N/imaging/R1238N'
    # fsfolder = '/data/eeg/freesurfer/subjects/R1238N'
    og_dir = os.getcwd()
    corrfile = os.path.join(outfolder, sub + '_shift_corrected.csv')

    if os.path.isfile(corrfile) and not overwrite:
        print("Corrected csv file already exists for " + sub + ". Use 'overwrite=True' to overwrite results.")
        return -1

    ### get data and save them to files that R can read
    elnames = loc.get_contacts()
    coords = loc.get_contact_coordinates('fs', elnames)
    eltypes = loc.get_contact_types(elnames)
    bpairs = loc.get_pairs()
    [lhvertex, _, lhname] = nb.freesurfer.io.read_annot( os.path.join(fsfolder, 'label', 'lh.aparc.annot') )
    [rhvertex, _, rhname] = nb.freesurfer.io.read_annot( os.path.join(fsfolder, 'label', 'rh.aparc.annot') )
    savetxt(os.path.join(outfolder, sub + '_shift_coords.csv'), coords, delimiter=',')
    savetxt(os.path.join(outfolder, sub + '_shift_eltypes.csv'), eltypes, fmt='%s')
    savetxt(os.path.join(outfolder, sub + '_shift_bpairs.csv'), bpairs, fmt='%s', delimiter=',')
    savetxt(os.path.join(outfolder, sub + '_shift_elnames.csv'), elnames, fmt='%s')
    savetxt(os.path.join(outfolder, sub + '_shift_lhvertex.csv'), lhvertex, fmt='%s')
    savetxt(os.path.join(outfolder, sub + '_shift_lhname.csv'), lhname, fmt='%s')
    savetxt(os.path.join(outfolder, sub + '_shift_rhvertex.csv'), rhvertex, fmt='%s')
    savetxt(os.path.join(outfolder, sub + '_shift_rhname.csv'), rhname, fmt='%s')
    ###

    os.chdir(osp.join(here,'brainshift'))

    ### prepare R command and run

    cmd_args = "'--args sub=\"{sub}\" outfolder=\"{outfolder}\" fsfolder=\"{fsfolder}\"'".format(
        sub=sub,outfolder=outfolder,fsfolder=fsfolder
    )
    logfile = os.path.join(outfolder, sub + '_shiftCorrection.Rlog')
    cmd = ["R", "CMD", "BATCH", "--no-save", "--no-restore", cmd_args,Rcorrection, logfile]
    logger.debug('Executing shell command %s'%str(cmd))
    call(' '.join(cmd),shell=True)
    ###

    os.chdir(og_dir)
        ### load the corrected output
    corrected_data = pd.DataFrame.from_csv(corrfile)
    newnames=corrected_data.index.values


    # put data in loc
    loc.set_contact_coordinates('fs', newnames, corrected_data[['corrx','corry','corrz']].values, coordinate_type='corrected')
    loc.set_contact_infos('displacement', newnames, corrected_data.displaced.values)
    loc.set_contact_infos('closest_vertex_distance', newnames,corrected_data.closestvertexdist.values)
    loc.set_contact_infos('linked_electrodes', newnames, corrected_data.linkedto.values)
    loc.set_contact_infos('link_displaced', newnames, corrected_data.linkdisplaced.values)
    loc.set_contact_infos('group_corrected', newnames, corrected_data['group'].values)
    loc.set_contact_infos('closest_vertex_coordinate', newnames,
                          corrected_data[['closestvertexx','closestvertexy','closestvertexz']].values.tolist())
    loc.set_contact_labels('dk', newnames, corrected_data.DKT.values)
    loc.set_contact_coordinates('fsaverage', newnames, corrected_data[['fsavg_x','fsavg_y','fsavg_z']].values.tolist(), coordinate_type='corrected')
    ###
    os.remove(os.path.join(outfolder, sub + '_shift_coords.csv'))
    os.remove(os.path.join(outfolder, sub + '_shift_eltypes.csv'),)
    os.remove(os.path.join(outfolder, sub + '_shift_bpairs.csv'))
    os.remove(os.path.join(outfolder, sub + '_shift_elnames.csv'))
    
    os.remove(os.path.join(outfolder, sub + '_shift_lhvertex.csv'))
    os.remove(os.path.join(outfolder, sub + '_shift_lhname.csv'))
    os.remove(os.path.join(outfolder, sub + '_shift_rhvertex.csv'))
    os.remove(os.path.join(outfolder, sub + '_shift_rhname.csv'))
    
    return loc
