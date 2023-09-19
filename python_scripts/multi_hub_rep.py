from asyncore import file_wrapper
import datasets
import tensorflow as tf
import tensorflow.core
import tensorflow_hub as hub
import json
import numpy as np
import os
import analysis
import itertools
import pandas as pd
from datetime import datetime
import torch
from torchvision import transforms
import cv2
from torchvision.models.feature_extraction import create_feature_extractor
import transformers
import random
import tensorflow_addons as tfa
from tensorflow.keras.datasets import cifar10
import tensorflow_datasets as tfds
import PIL
from PIL import Image
import shutil
from torch.utils.data import Dataset
import timm
import hubReps
import analysis
import csv
import math
import random
from itertools import chain


# get basics working, threshhld, does it work for multiple models
# look into new tasks when finished
# standalone, the 3 tasks
# standalone repository, archive link to paper in review, describes the 3 tasks
# not doing the matching task anymore for humans, hard for human data


def image_list(data_dir):
    img_files = os.listdir(data_dir)
    image_names = []
    for file in img_files:
        image_names.append(file)
    return image_names

def rep_maker(data_dir, modelFile, model_name, modelData, model, batch_size):
    # get dataset from datasets.py
    dataset = get_dataset(data_dir, modelFile, model_name, modelData, model, batch_size)
    #print('\nDataset size:', dataset, '\n')

    # get reps from hubReps.py
    # could have a pointer error with iterations.
    return get_reps(modelFile, model, dataset, modelData, args.batch_size)


def learning_exemplar(image_names, reps, csv_file, data_dir):
    
    # do simple deterministic, reps might just be faulty enough??
    # add noise (have to tune noise level)
    # add noise on image, or just on representations (gaussian)
    # noise parameter might need to be tuned for each parameter
    # give every image, ge tall reps, get std dev, add noise based of std dev
    # possible to give all models same models, not unreasonable start, but might need to be changed
    # look at poplular authors, find paper, see if interesting / want to present
    # google scholar Deep neural networks neuroscience
    # 1/2 the lab are models, other 1/2 are neuroscience people, find intersection
    # kriegesorgte/decarlo recents` ??
    image_sets = image_sets_maker(csv_file, image_names, reps, 'le')
    euc_correct_total = 0
    num_total = 0
    answer_set = []
    # [row_idx, target_idx, image1_idx, image2_idx, target_name, image1_name, image2_name, euc_dist_target, euc_dist_1, euc_dist_2, CorrRes]
    for set in image_sets:
        target_euc_min = min(set[-4])
        foil1_euc_min = min(set[-3])
        foil2_euc_min = min(set[-2])
        CorrRes = set[-1]
        if (target_euc_min < foil1_euc_min) and (target_euc_min < foil2_euc_min):
            choice = 'target'
            answer = 'correct'
            euc_correct_total += 1
        elif (foil1_euc_min < target_euc_min) and (foil1_euc_min < foil2_euc_min):
            choice = 'foil1'
            answer = 'incorrect'
        else:
            choice = 'foil2'
            answer = 'incorrect'
        answer_set.append([answer, choice])
        num_total +=1
    '''''
    print(f'\n\n\nUsing Model: {args.model_name}\n-------------\n\
Euc Learning Exemplar Correct: {euc_correct_total} / {num_total}\n')
    '''''
    return [euc_correct_total, num_total, answer_set]

def many_oddball(image_names, reps, csv_file, data_dir):
    image_sets = image_sets_maker(csv_file, image_names, reps, 'odd')
    euc_correct_total = 0
    num_total = 0
    answer_set = []
    for set in image_sets:
        euc_min = min([set[-4], set[-3], set[-2]])
        if euc_min == set[-4]:
            choice = 3
        elif euc_min == set[-3]:
            choice = 2
        elif euc_min == set[-2]:
            choice = 1
        else:
            raise ValueError('Best Distance not found among image_sets')
        # [row_idx, image1_idx, image2_idx, image3_idx,
        #  image1_name, image2_name, image3_name,
        #  euc_dist_1_2, euc_dist_1_3, euc_dist_2_3, CorrRes]
        if (int(set[-1]) == choice):
            answer = 'correct'
            euc_correct_total += 1
        else:
            answer = 'incorrect'

        #print(f'{int(set[-1])} || {choice} || {answer}')
        answer_set.append([answer, choice])
        num_total +=1
    '''''
    print(f'\n\n\nUsing Model: {args.model_name}\n-------------\n\
Euc Many Oddball Correct: {euc_correct_total} / {num_total}\n')
    '''''
   
    return [euc_correct_total, num_total, answer_set]

# look for object with biggest distance from the other two
# is that different than taking min??
# make sure they are the same
# look toward trials to see how maybe people favoredo one of the other
# mathamatical proof?? or just show emperically...
def three_ACF(image_names, reps, csv_file, data_dir):
    img_files = os.listdir(data_dir)
    for file in img_files:
        img = Image.open(os.path.join(data_dir, file))
        if img.size == (203, 470):
            left = 2
            top = 0
            right = 202
            bottom = 200
            img_altered = img.crop((left, top, right, bottom))
            img_altered.save(os.path.join(data_dir, file))
    image_sets = image_sets_maker(csv_file, image_names, reps, 3)
    euc_correct_total = 0
    num_total = 0
    answer_set = []
    for set in image_sets:
        euc_min = min([set[-4], set[-3], set[-2]])
        if euc_min == set[-4]:
            choice = 1
        elif euc_min == set[-3]:
            choice = 2
        elif euc_min == set[-2]:
            choice = 3
        else:
            raise ValueError('Best Distance not found among image_sets')
        # [row_idx, image1_idx, image2_idx, image3_idx, target_idx, image1_name, 
        # image2_name, image3_name, target_image, euc_dist_1, euc_dist_2, euc_dist_3, CorrRes])
        if (int(set[-1]) == choice):
            answer = 'correct'
            euc_correct_total += 1
        
        else:
            answer = 'incorrect'
        
        answer_set.append([answer, choice])
        #print(f'{int(set[-1])} || {choice} || {answer}')
        num_total +=1
  
    print(f'\n\n\nUsing Model: {args.model_name}\n-------------\n\
Euc 3ACF Correct: {euc_correct_total} / {num_total}\n')

    return [euc_correct_total, num_total, answer_set]
    


def normalize(arr, t_min, t_max):
    norm_arr = []
    diff = t_max - t_min
    diff_arr = max(arr) - min(arr)   
    for i in arr:
        temp = (((i - min(arr))*diff)/diff_arr) + t_min
        norm_arr.append(temp)
    return norm_arr

def LBA(dist, c=1, ß=None, b=1, A=1, k=0, t0=0):

    n = math.exp((-c * dist))
    if ß is None:
        ß = n
    v = n / (n + ß)
    diff_score = 1 - v
    #a = random.randrange(0, A)
    #k = b - A
    drift_rate_same = np.random.normal(v, 1)
    drift_rate_diff = np.random.normal(diff_score, 1)
    
    rt_same = ((b - k) / drift_rate_same) + t0
    rt_diff = ((b - k) / drift_rate_diff) + t0

    if rt_same < rt_diff:
        return ['same', 1, rt_same]
    else:
        return ['diff', 2, rt_diff]


def same_diff(image_names, reps, csv_file):
    # get sets of images with correct result and reps
    image_sets = image_sets_maker(csv_file, image_names, reps, 2)

    euc_correct_total = 0
    #LBA_correct_total = 0
    euc_correct_factor_total = 0
    #LBA_correct_factor_total = 0
    euc_incorrect_factor_total = 0
    #LBA_incorrect_factor_total = 0
    num_total = 0
    all_euc_comparisons = []
    #all_LBA_comparisons = []
    answer_set = []
    for comparison in image_sets:
        euc_factor = comparison[-2] #/ (comparison[-2] - 0.002)
        all_euc_comparisons.append(euc_factor)
        #all_LBA_comparisons.append(comparison[-1][1])
    normed_eucs = normalize(all_euc_comparisons, 0, 1)
   #normed_LBAs = normalize(all_euc_comparisons, 0, 1)

    idx = 0
    for euc_score in normed_eucs:
        if euc_score < 0.5:
            euc_result = ['same',1]
        else:
            euc_result = ['diff',2]
        
        if (image_sets[idx][-3] == euc_result[0]) or (int(image_sets[idx][-3]) == euc_result[1]):
            euc_ans = 'correct'
            euc_correct_total += 1
        
            euc_correct_factor_total += euc_score
        else:
            euc_ans = 'incorrect'
            euc_incorrect_factor_total += euc_score
        '''
        if (comparison[-3] == comparison[-1][0]) or (int(comparison[-3]) == comparison[-1][1]):
            LBA_ans = 'correct'  
        else:
            LBA_ans = 'not correct'
        
        print('Correct Answer:', image_sets[idx][-3], '| Given:', euc_result, f'({euc_ans})', '| Euc Factor:', euc_score)
        
        if euc_ans == 'correct':
            euc_correct_total += 1
            euc_correct_factor_total += euc_score #comparison[-2]
        else:
            euc_incorrect_factor_total += euc_score #comparison[-2]
        
        if LBA_ans == 'correct':
            LBA_correct_total += 1
            LBA_correct_factor_total += comparison[-1][1]
        else:
            LBA_incorrect_factor_total += comparison[-1][1]
        '''
        answer_set.append([euc_score, euc_ans])
        num_total +=1
        idx += 1

    #print('normed_eucs:\n', normed_eucs)
    #print('normed_LBAs:', normed_LBAs)
    '''''
    LBA_factor_total = LBA_correct_factor_total + LBA_incorrect_factor_total
    euc_factor_total = euc_correct_factor_total + euc_incorrect_factor_total

    if euc_correct_total != 0:
        euc_correct_avg = euc_correct_factor_total / euc_correct_total
    else:
        euc_correct_avg = "No Euc was correct"
    if LBA_correct_total != 0:
        LBA_correct_avg = LBA_correct_factor_total / LBA_correct_total
    else:
        LBA_correct_avg = "No LBA was correct"
    euc_incorrect_avg = euc_incorrect_factor_total / (num_total - euc_correct_total)
    LBA_incorrect_avg = LBA_incorrect_factor_total / (num_total - LBA_correct_total)
    

    print(f'\n\n\nUsing Model: {args.model_name}\n-------------\n\
Euc Correct: {euc_correct_total} / {num_total}\n\
LBA Correct: {LBA_correct_total} / {num_total}\n\
Average Factor for correct Euc: {euc_correct_avg}\n\
Average Factor for correct LBA: {LBA_correct_avg}\n\
Average Factor for incorrect Euc: {euc_incorrect_avg}\n\
Average Factor for incorrect LBA: {LBA_incorrect_avg}\n')
    '''''
    return [euc_correct_total, num_total, answer_set]


def image_sets_maker(csv_file, image_names, reps, num_sets):
    
    with open(csv_file, newline='') as c:
        image_set = []
        csv_data = csv.reader(c)

        image_sets = []
        row_idx = 0
        for row in csv_data:
            if row_idx > 0:
                if num_sets == 2:
                    image1_name = row[5].replace('.jpg', '.tif')
                    image2_name = row[6].replace('.jpg', '.tif')
                    CorrRes = row[2]
                    image1_idx = image_names.index(image1_name)
                    image2_idx = image_names.index(image2_name)
                    euc_dist = euclidean_distance(reps[image1_idx], reps[image2_idx])
                    #LBA_results = LBA(euc_dist)
                    LBA_results = None
                    image_sets.append([row_idx, image1_idx, image2_idx, image1_name, image2_name, CorrRes, euc_dist, LBA_results])
                elif num_sets == 3:
                    image1_name = f'trial{row_idx}-1.jpg'
                    image2_name = f'trial{row_idx}-2.jpg'
                    image3_name = f'trial{row_idx}-3.jpg'
                    target_image = f'trial{row_idx}-target.jpg'
                    image1_idx = image_names.index(image1_name)
                    image2_idx = image_names.index(image2_name)
                    image3_idx = image_names.index(image3_name)
                    target_idx = image_names.index(target_image)
                    euc_dist_1 = euclidean_distance(reps[target_idx], reps[image1_idx])
                    euc_dist_2 = euclidean_distance(reps[target_idx], reps[image2_idx])
                    euc_dist_3 = euclidean_distance(reps[target_idx], reps[image3_idx])
                    CorrRes = row[1]
                    image_sets.append([row_idx, image1_idx, image2_idx, image3_idx, target_idx, image1_name, image2_name, image3_name, target_image, euc_dist_1, euc_dist_2, euc_dist_3, CorrRes])
                elif num_sets == 'odd':
                    image1_name = f'trial{row_idx}-1.jpg'
                    image2_name = f'trial{row_idx}-2.jpg'
                    image3_name = f'trial{row_idx}-3.jpg'
                    image1_idx = image_names.index(image1_name)
                    image2_idx = image_names.index(image2_name)
                    image3_idx = image_names.index(image3_name)
                    euc_dist_1_2 = euclidean_distance(reps[image1_idx], reps[image2_idx])
                    euc_dist_1_3 = euclidean_distance(reps[image1_idx], reps[image3_idx])
                    euc_dist_2_3 = euclidean_distance(reps[image2_idx], reps[image3_idx])
                    CorrRes = row[1]
                    image_sets.append([row_idx, image1_idx, image2_idx, image3_idx, image1_name, image2_name, image3_name, euc_dist_1_2, euc_dist_1_3, euc_dist_2_3, CorrRes])
                elif num_sets == 'le':
                    euc_dist_1 = []
                    euc_dist_2 = []
                    euc_dist_target = []
                    set6 = ['nz1_4_a.tif', 'nz1_12_b.tif', 'nz1_30_a.tif', 'nz1_75_a.tif', 'nz1_70_b.tif', 'nz1_77_b.tif']
                    foil1_name = row[-2] + '.tif'
                    foil2_name = row[-1] + '.tif'
                    target_name = row[2] + '.tif'
                    foil1_idx = image_names.index(foil1_name)
                    foil2_idx = image_names.index(foil2_name)
                    target_idx = image_names.index(target_name)
                    for img6 in set6:
                        img6_idx = image_names.index(img6)
                        euc_dist_target.append(euclidean_distance(reps[img6_idx], reps[target_idx]))
                        euc_dist_1.append(euclidean_distance(reps[img6_idx], reps[foil1_idx]))
                        euc_dist_2.append(euclidean_distance(reps[img6_idx], reps[foil2_idx]))
                    CorrRes  = row[3]
                    image_sets.append([row_idx, target_idx, foil1_idx, foil2_idx, target_name, foil1_name, foil2_name, euc_dist_target, euc_dist_1, euc_dist_2, CorrRes])
                else:
                    raise ValueError(f"Number of sets ({num_sets}) is not available")


            row_idx += 1

    return image_sets
        
    print(image_sets)
    image1_idx = image_names.index(image1_name)
    idx1 = image_sets[2][1]
    idx2 = image_sets[2][2]
    euc_dist = euclidean_distance(reps[idx1], reps[idx2])

def euclidean_distance(x1, x2):
    temp = x1 - x2
    squared_value = np.dot(temp.T, temp)
    euc_dist = np.sqrt(squared_value)
    return euc_dist

def load_image_set(data_dir, row, row_idx):
    #img_files = os.listdir(data_dir)
    #csv_file.read_line()
    image1_name = row[5].replace('.jpg', '.tif')
    image2_name = row[6].replace('.jpg', '.tif')
    image1 = Image.open(os.path.join(data_dir, image1_name))
    image2 = Image.open(os.path.join(data_dir, image2_name))
    CorrRes = row[2]
    image_set = [row_idx, image1_name, image2_name, CorrRes]

    return image_set

def find_model(fileList, modelName):
    fileList = fileList.split(', ')
    for file in fileList:
        with open(file, "r") as f:
            hubModels = json.loads(f.read())
            if modelName in hubModels:
                modelFile = file
                modelData = hubModels[modelName]

    return modelFile, modelData


def get_model(modelName, modelFile, hubModels):
    if modelFile == "./hubModels.json":
        # Creating models
        info = hubModels[modelName]
        shape = info["shape"] if "shape" in info.keys() else [224, 224, 3]
        # Create model from tfhub
        inp = tf.keras.Input(shape=shape)
        out = hub.KerasLayer(info["url"])(inp)
        model = tf.keras.Model(inputs=inp, outputs=out)
    elif modelFile == "./hubModels_keras.json":
        # Create model from keras function
        model = hubReps.get_keras_model(hubModels, modelName)[0]
    elif (modelFile == "./hubModels_pytorch.json") or \
        (modelFile == "./hubModels_timm.json") or \
        (modelFile == "./hubModels_transformers.json") or \
        (modelFile == "./hubModels_pretrainedmodels.json"):
        # Create model from pytorch hub
        model = hubReps.get_pytorch_model(hubModels, modelFile, modelName)
    else:
        raise ValueError(f"Unknown models file {modelFile}")

    return model


def get_dataset(data_dir, modelFile, modelName, modelData, model, batch_size=64):
    if modelFile == "./hubModels.json" or modelFile == "./hubModels_keras.json":
        preprocFun = datasets.preproc(
            **modelData,
            labels=False,
        )
        dataset = datasets.get_flat_dataset(data_dir, preprocFun, batch_size=64)

    elif modelFile == "./hubModels_pytorch.json" \
            or modelFile == "./hubModels_pretrainedmodels.json" \
            or modelFile == "./hubModels_timm.json" \
            or modelFile == "./hubModels_transformers.json":

        # using pytorch model

        dataset = datasets.get_pytorch_dataset(
            data_dir, modelData, model, batch_size, modelName
        )

    else:
        raise ValueError(f"Unknown models file {modelFile}")
    
    return dataset


def get_reps(modelFile, model, dataset, modelData, batch_size=64):
    
    if modelFile == "./hubModels.json" or modelFile == "./hubModels_keras.json":
        reps = hubReps.get_reps(
            model, dataset, modelData, batch_size
        )

    elif modelFile == "./hubModels_pytorch.json" \
            or modelFile == "./hubModels_pretrainedmodels.json" \
            or modelFile == "./hubModels_timm.json" \
            or modelFile == "./hubModels_transformers.json":
        
        reps = hubReps.get_pytorch_reps(
            model, dataset, modelData, batch_size
        )

    return reps



if __name__ == "__main__":
    import argparse
    
    os.environ['TORCH_HOME'] = '/data/brustdm/modelnet/torch'

    parser = argparse.ArgumentParser(
        description="Get representations from Tensorflow Hub networks using the validation set of ImageNet, intended to be used in HPC"
    )
    parser.add_argument(
        "--model_name",
        "-m",
        type=str,
        help="name of the model to get representations from",
    )
    parser.add_argument(
        "--index",
        "-i",
        type=int,
        help="index of the model to get representations from",
        default=0
    )
    parser.add_argument(
        "--batch_size",
        "-b",
        type=int,
        default=64,
        help="batch size for the images passing through networks",
    )
    parser.add_argument(
        "--data_dir",
        "-d",
        type=str,
        help="directory of the image dataset",
        default="../novset",
    )
    parser.add_argument(
        "--comp_dir",
        "-cd",
        type=str,
        help="directory of the compared images",
        default="./data_storage/temp_images",
    )
    parser.add_argument(
        "--model_files",
        "-f",
        type=str,
        help=".json file with the hub model info",
        default="./hubModels.json, ./hubModels_timm.json, ./hubModels_keras.json, ./hubModels_pytorch.json"
    )
    parser.add_argument(
        "--feature_limit",
        "-l",
        type=int,
        help="the maximum number of features a representation can have",
        default=2048,
    )
    parser.add_argument(
        "--reps_name",
        type=str,
        help="name of the representations to save",
        default="temp_reps"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="name of the dataset to use, use 'test' for testing a model",
        default="test"
    )
    parser.add_argument(
        "--reps",
        type=bool,
        default=False,
        help="indicates whether all reps are being calculated"
    )
    parser.add_argument(
        "--simSet",
        type=str,
        default="all",
        help="which set of similarity functions to use",
    )
    parser.add_argument(
        "--csv_file",
        "-cf",
        type=str,
        default="./data_storage/ziggerins_trials.csv",
        help="which csv of trial to use",
    )
    parser.add_argument(
        "--test",
        "-t",
        type=str,
        help="which trial type to use",
    )
    args = parser.parse_args()


    if args.reps:
        if args.index < 785:
            print('idx:', args.index)
            results = []
            model_list = []
            for model_file in args.model_files:
                with open('../python_scripts/hubModels_timm.json', "r") as f:
                    hubModels = json.loads(f.read())
                    model_list.append([*hubModels])
            # model_list = ['crossvit_tiny_240']
            model_list = list(chain(*model_list))
            problems = ['cait_s24_384']
            for problem in problems:
                model_list.remove(problem)
            model_name = model_list[args.index]
            print('\nUsing:', model_name)
            if 5 == 5:
               # print(f'New Addition: {model_name}')
                #results.append(model_name)
                modelFile, modelData = find_model(args.model_files, model_name)
                # getting modelFile data
                with open(modelFile, "r") as f:
                    hubModels = json.loads(f.read())

                    # get model from hubReps.py
                    model = get_model(model_name, modelFile, hubModels)

                if args.test == 'same_diff':
                    ddir = '../novset'
                    reps = rep_maker(ddir, modelFile, model_name, modelData, model, args.batch_size)
                    image_names = image_list(ddir)
                    results.append(same_diff(image_names, reps,
                                             '../python_scripts/data_storage/ziggerins_trials_full.csv'))
                elif args.test == '3ACF':

                    if os.path.exists('../python_scripts/data_storage/3ACF_results.npy'):
                        results_full = np.load('../python_scripts/data_storage/3ACF_results.npy',
                                               allow_pickle=True)
                    else:
                        results_full = []

                    if model_name not in results_full:
                        print(f'New Addition for 3ACF: {model_name}')
                        results.append(model_name)
                        ddir = '../python_scripts/standalone/3AFCMatching/stimuli_altered'
                        reps = rep_maker(ddir, modelFile, model_name, modelData, model, args.batch_size)
                        image_names = image_list(ddir)
                        results.append([model_name, 
                            three_ACF(image_names, reps, '../python_scripts/data_storage/3ACF_trials.csv',
                                      ddir)])
                        if os.path.exists('../python_scripts/data_storage/3ACF_results.npy'):
                            results_full = np.load('../python_scripts/data_storage/3ACF_results.npy',
                                                   allow_pickle=True)
                            results_full = np.append(results_full, results)
                        else:
                            results_full = results
                        np.save('../python_scripts/data_storage/3ACF_results.npy', results_full)
                    else:
                        print(f'Already have model for 3ACF: {model_name}')

                elif args.test == 'many_odd':
                    if os.path.exists('../python_scripts/data_storage/many_odd_results.npy'):
                        results_full = np.load('../python_scripts/data_storage/many_odd_results.npy',
                                               allow_pickle=True)
                    else:
                        results_full = []
                    if model_name not in list(results_full):
                        print(f'New Addition for ManyOdd: {model_name}')
                        results.append(model_name)
                        ddir = '../python_scripts/standalone/ManyObjectsOddball/stimuli'
                        reps = rep_maker(ddir, modelFile, model_name, modelData, model, args.batch_size)
                        image_names = image_list(ddir)
                        results.append(many_oddball(image_names, reps,
                                                    '../python_scripts/data_storage/many_oddball_trials.csv',
                                                    ddir))
                        if os.path.exists('../python_scripts/data_storage/many_odd_results.npy'):
                            results_full = np.load('../python_scripts/data_storage/many_odd_results.npy',
                                                   allow_pickle=True)
                            results_full = np.append(results_full, results)
                        else:
                            results_full = results
                        np.save('../python_scripts/data_storage/many_odd_results.npy', results_full)
                    else:
                        print(f'Already have model for many_odd: {model_name}')

                elif args.test == 'learn_exemp':
                    if os.path.exists('../python_scripts/data_storage/learn_exemp_results.npy'):
                        results_full = np.load('../python_scripts/data_storage/learn_exemp_results.npy',
                                               allow_pickle=True)
                    else:
                        results_full = []
                    if model_name not in results_full:
                        print(f'New Addition for lr: {model_name}')
                        results.append(model_name)
                        ddir = '../novset_lr'
                        reps = rep_maker(ddir, modelFile, model_name, modelData, model, args.batch_size)
                        image_names = image_list(ddir)
                        results.append(learning_exemplar(image_names, reps,
                                                         '../python_scripts/data_storage/learning_exemplar_trials.csv',
                                                         ddir))
                        if os.path.exists('../python_scripts/data_storage/learn_exemp_results.npy'):
                            results_full = np.load('../python_scripts/data_storage/learn_exemp_results.npy',
                                                   allow_pickle=True)
                            results_full = np.append(results_full, results)
                        else:
                            results_full = results
                        np.save('../python_scripts/data_storage/learn_exemp_results.npy', results_full)
                        #print(*results, sep='\n')
                    else:
                        print(f'Already have model for lr: {model_name}')
            else:
                print(f'Already have model for lr: {model_name}')
    else:
        modelFile, modelData = find_model(args.model_files, args.model_name)

        # getting modelFile data
        with open(modelFile, "r") as f:
            hubModels = json.loads(f.read())

            # get model from hubReps.py
            model = get_model(args.model_name, modelFile, hubModels)

        reps = rep_maker(args.data_dir, modelFile, args.model_name, modelData, model, args.batch_size)
        # get list of image names
        img_files = os.listdir(args.data_dir)
        image_names = []
        for file in img_files:
            image_names.append(file)
        if args.test == 'same_diff':
            reults = same_diff(image_names, reps,
                               '../python_scripts/data_storage/ziggerins_trials_full.csv')
        elif args.test == 'choose_3':
            reults = three_ACF(image_names, reps, args.csv_file, args.data_dir)
        elif args.test == 'many_odd':
            reults = many_oddball(image_names, reps, args.csv_file, args.data_dir)
        elif args.test == 'learn_exemp':
            reults = learning_exemplar(image_names, reps, args.csv_file, args.data_dir)
        elif args.test == 'all':
            results = []
            results.append(same_diff(image_names, reps,
                                     '../python_scripts/data_storage/ziggerins_trials_full.csv'))
            results.append(
                three_ACF(image_names, reps, '../python_scripts/data_storage/3ACF_trials.csv'))
            results.append(many_oddball(image_names, reps,
                                        '../python_scripts/data_storage/many_oddball_trials.csv',
                                        '../python_scripts/standalone/ManyObjectsOddball/stimuli'))
            results.append(learning_exemplar(image_names, reps,
                                             '../python_scripts/data_storage/learning_exemplar_trials.csv',
                                             '../novset'))

        for result in results:
            print(f'SD Correct: {result[0]} / {result[1]}')
            print(f'3ACF Correct: {result[0]} / {result[1]}')
            print(f'MOO Correct: {result[0]} / {result[1]}')
            print(f'LE Correct: {result[0]} / {result[1]}')
            # print(f'\n\n\nUsing Model: {args.model_name}\n-------------\n\
    # Comparing: {comparison[3]} | {comparison[4]}\nEuclidean Distance is: {comparison[-2]}\nImages are seen as {euc_result} by this metric\n\
    # LBA Decision is {comparison[-1][0]} with a "response time" of {comparison[-1][1]}\n\
    # Correct answer: {comparison[-3]}\n\
    # Model is {euc_ans} by Euclidian Distance and {LBA_ans} by LBA for this image set\n')

    # make more sensible for large sets of models, directory modification very slow
    # make representations all at once
    # index out of the matrix
    # could compare a similarity matrix instead for all combos
    # then just look for right cell in matrix to find
    # one script for all, another for locating, indexing
    # paper over LBA, cognitive link function, just need to select params

    # need to output like human data later

    # make the output csv (or numpy) per trial!!!
    # especially for learning_exemplar,
    #       probably only wrong on rotations and noise
    # for many odd_ball make larges image the size
    #       add whitespace to smaller so that it is the largest size
    # could equalize the sizes to see but maybe not
    # initial task should be faithful, add white border