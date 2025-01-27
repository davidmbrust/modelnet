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
import datetime
import torch
from torchvision import transforms
import cv2
import torchvision
from torchvision.models.feature_extraction import create_feature_extractor
import timm
import pretrainedmodels
import transformers
import torch.nn as nn
import hubReps

def count_recurrent_layers(model):
    recurrent_layer_count = 0
    for layer in model.modules():
        if isinstance(layer, (nn.LSTM, nn.GRU, nn.RNN)):
            recurrent_layer_count += 1
    return recurrent_layer_count


def is_likely_dimension_matching(module):
    """
    Heuristic to guess if the module potentially matches input-output dimensions.
    This is a simplified check and may not cover all cases or architectures.
    """
    for layer in module.modules():
        if isinstance(layer, torch.nn.Conv2d):
            # Check if the convolution is likely to maintain spatial dimensions
            if layer.stride == (1, 1) and layer.kernel_size in [(1, 1), (3, 3)]:
                # Assuming padding is set to maintain dimensions for kernel_size 3
                return True
            # Additional checks for other layers or configurations can be added here
    return False

def has_potential_residual_structure(module):
    """
    Combines checks for residual-like structure and dimension matching.
    """
    return has_residual_connection(module) and is_likely_dimension_matching(module)

def extract_layer_info_and_count_residuals(module, parent_name='', residual_counter=None):
    if residual_counter is None:
        residual_counter = collections.defaultdict(int)

    layer_info = {}
    for name, layer in module.named_children():
        layer_name = f"{parent_name}.{name}" if parent_name else name

        # Check if the module potentially represents a true residual block
        if has_potential_residual_structure(layer):
            residual_counter[layer.__class__.__name__] += 1

        # Recursively inspect child modules
        children_info, residual_counter = extract_layer_info_and_count_residuals(
            layer, parent_name=layer_name, residual_counter=residual_counter)

        layer_info[layer_name] = {
            'type': layer.__class__.__name__,
            'children': children_info
        }

    return layer_info, residual_counter

def has_residual_connection(module):
    # List known residual block types here
    residual_block_types = ['Bottleneck', 'BasicBlock']
    return module.__class__.__name__ in residual_block_types


def revise_names(names):
    idx = 0
    new_names = model_names
    unused_list = ['vgg', 'tf_efficientnet', 'efficientnet', 'densenet', 'mobilenet', 'resnet', 'tf_mobilenet',
                   'convnext', 'deit3_medium_patch16_224_in21ft1k', 'pvt_v2_b5', 'vit_giant_patch14_224_clip_laion2b', 'xcit_medium_24_p16_224_dist']
    for i in new_names:
        n = 0
        while n <= (len(unused_list) - 1):
            if i.startswith(unused_list[n]):
                del new_names[idx]
            n += 1
        idx += 1

    return new_names

def add_json(i, new_data):
    with open(args.models_file, "r+") as f:
        json_d = json.loads(f.read())
        json_d[i] = new_data
        f.seek(0)
        json.dump(json_d, f, indent=4)


def write_json(new_data):
    with open(args.models_file, "w") as f:
        hubModels[name_i].update(new_data)
        f.seek(0)
        json.dump(hubModels, f, indent=4)

def get_model(name, name_i):
    if args.models_file == "../data_storage/hubModel_storage/hubModels_keras.json":
        function = hubModels[name_i]['function']
        model_full = eval(function)
        inp = model_full.input
        layerName = model_full.layers[int(hubModels[name_i]['layerIdx'])].name
        out = model_full.get_layer(layerName).output
        model = tf.keras.Model(inputs=inp, outputs=out)
    elif args.models_file == "../data_storage/hubModel_storage/hubModels_pytorch.json":
        function = name['function']
        model_full = eval("torch.hub.load" + function)
        x = name["shape"] if "shape" in name else [224, 224, 3]
        x.insert(0, 1)
        temp_data = torch.rand(x)
        if len(name["outputLayer"]) > 1:
            a = name["outputLayer"][1]
            b = name["outputLayer"][0]
            return_nodes = {
                a: b
            }
        else:
            return_nodes = name["outputLayer"]
        model = create_feature_extractor(model_full, return_nodes=return_nodes)

    elif args.models_file == "../data_storage/hubModel_storage/hubModels_pretrainedmodels.json":
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context

    elif args.models_file == "../data_storage/hubModel_storage/hubModels_transformers.json":

        function = name['func']
        extractor_func = name['extractor_func']
        model = eval('transformers.' + function + f'.from_pretrained("{name_i}")')
        model_de = eval('transformers.' + extractor_func + f'.from_pretrained("{name_i}")')
    
    elif args.models_file == "../data_storage/hubModel_storage/hubModels_timm.json":
        model = hubReps.get_pytorch_model(hubModels, args.models_file, name_i)

    else:
        shape = name["shape"] if "shape" in name else [224, 224, 3]
        # Create model from tfhub
        inp = tf.keras.Input(shape=shape)
        out = hub.KerasLayer(name["url"])(inp)
        model = tf.keras.Model(inputs=inp, outputs=out)

    return model



def get_children(model: torch.nn.Module):
    # get children form model
    children = list(model.children())
    flatt_children = []
    if children == []:
        # if model has no children then model is last child
        return model
    else:
       # look for children to the last child!
       for child in children:
            try:
                flatt_children.extend(get_children(child))
            except TypeError:
                flatt_children.append(get_children(child))
    return flatt_children


def get_model_data(model, get_weights=False):
    if args.models_file == "../data_storage/hubModel_storage/hubModels_pytorch.json" \
            or args.models_file == "../data_storage/hubModel_storage/hubModels_timm.json" \
            or args.models_file == "../data_storage/hubModel_storage/hubModels_transformers.json":

        num_layers = len(get_children(model))
        for param in model.parameters():
            param.requires_grad = False
        num_params = sum(
            param.numel() for param in model.parameters()
        )
        if get_weights:
            model_weights = torchvision.models.get_model_weights(model)
        else:
            model_weights = None


    elif args.models_file != "../data_storage/hubModel_storage/hubModels_pytorch.json":
        num_layers = len(model.layers)
        num_params_train = np.sum([np.prod(v.get_shape()) for v in model.trainable_weights])
        num_params_non_train = np.sum([np.prod(v.get_shape()) for v in model.non_trainable_weights])
        num_params = int(num_params_train + num_params_non_train)
        if get_weights:
            model_weights = model.get_weights()
        else:
            model_weights = None

    else:
        raise ValueError(f"models file unsupported for getting data {args.dataset}")
    return num_params, num_layers, model_weights

def json_mod():
    with open(args.models_file, "r") as f:
        hubModels = json.loads(f.read())

    modelNames = list(hubModels.keys())
    idx = 0
    while (idx + 1) <= len(modelNames):
        name_i = modelNames[idx]
        print("Working on " + name_i + f" (Index {idx})")
        name = hubModels[name_i]
        if (("num_params" not in name) or ("num_layers" not in name)) and ("defunct" not in name):
            model = get_model(name)
            num_params, num_layers, model_weights = get_model_data(model)
            if "num_params" not in name:
                params_str = str(num_params)
                new_data = {"num_params": params_str}
                write_json(new_data)
            else:
                print(f"{name_i} already has data, skipping.")

            if "num_layers" not in name:
                layers_str = str(num_layers)
                new_data = {"num_layers": layers_str}
                write_json(new_data)
            else:
                print(f"{name_i} already has data, skipping.")

        else:
            print(f"{name_i} already has data, skipping.")

        idx += 1
    else:
        print("json modification completed")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="get model file and add model data where it doesnt exist"
    )
    parser.add_argument(
        "--models_file",
        "-f",
        type=str,
        help=".json file with the hub model info",
        default="../data_storage/hubModel_storage/hubModels_timm.json"
    )
    parser.add_argument(
        "--add",
        "-a",
        type=str,
        help=".json file with the hub model info",
        choices=["yes", "no"],
        default="no"
    )
    parser.add_argument(
        "--need_model",
        "-nm",
        type=str,
        help="indicates ned to load up model",
        choices=["yes", "no"],
        default="yes"
    )

    args = parser.parse_args()

    # Get the model info
    if args.models_file is not None:
        if args.add != "yes":
            with open(args.models_file, "r") as f:
                hubModels = json.loads(f.read())

            modelNames = list(hubModels.keys())
            idx = 0
            while (idx+1) <= len(modelNames):
                name_i = modelNames[idx]
                print("Working on " + name_i + f" (Index {idx})")
                name = hubModels[name_i]
                if (("num_params" not in name) or ("num_layers" not in name) or ("orign" not in name) or ("recurrent_layers" not in name)) and ("defunct" not in name):
                    if args.need_model is "yes":
                        model = get_model(name, name_i)
                        num_params, num_layers, model_weights = get_model_data(model)
                        if "num_params" not in name:
                            params_str = str(num_params)
                            new_data = {"num_params": params_str}
                            write_json(new_data)
                        else:
                            print(f"{name_i} already has data, skipping.")

                        if "num_layers" not in name:
                            layers_str = str(num_layers)
                            new_data = {"num_layers": layers_str}
                            write_json(new_data)
                        else:
                            print(f"{name_i} already has data, skipping.")

                    if "origin" not in name:
                        if args.models_file == "../data_storage/hubModel_storage/hubModels.json":
                            new_data = {"origin": "tenorflowHub"}
                            write_json(new_data)
                        if args.models_file == "../data_storage/hubModel_storage/hubModels_pytorch.json":
                            new_data = {"origin": "pytorch"}
                            write_json(new_data)
                    
                    if "recurrent_layers" not in name:
                        if args.models_file == "../data_storage/hubModel_storage/hubModels_timm.json":
                            if args.need_model is "yes":
                                num_recurrent = count_recurrent_layers(model)
                                new_data = {"recurrent_layers": num_recurrent}


                else:
                    print(f"{name_i} already has data, skipping.")

                idx += 1
            else:
                print("json modification completed")
        else:
            if args.models_file == "../data_storage/hubModel_storage/hubModels_timm.json":
                model_names = timm.list_models(pretrained=True)
                new_model_names = revise_names(model_names)
                new_model_names = revise_names(new_model_names)
                new_model_names = revise_names(new_model_names)
                n = 0
                for i in new_model_names:
                    print("Working on " + i + f" (Index {n})")
                    with open(args.models_file, "r") as f:
                        hubModels = json.loads(f.read())
                    if i not in hubModels:
                        m = timm.create_model(i, pretrained=True, num_classes=0)
                        data = m.default_cfg
                        num_params, num_layers, model_weights = get_model_data(m)
                        data['num_params'] = num_params
                        data['num_layers'] = num_layers
                        add_json(i, data)
                    else:
                        print(f"{i} already in json, skipping.")
                    n += 1
            elif args.models_file == "../data_storage/hubModel_storage/hubModels_pretrainedmodels.json":
                idx = 0
                with open(args.models_file, "r") as f:
                    hubModels = json.loads(f.read())
                for name in pretrainedmodels.model_names:
                    print(name)
                    if name not in hubModels:
                        if 'imagenet' in pretrainedmodels.pretrained_settings[name]:
                            data = pretrainedmodels.pretrained_settings[name]['imagenet']
                        else:
                            data = pretrainedmodels.pretrained_settings[name]['imagenet+5k']
                        other = {"origin": "pretrainedmodels", "parameters": "default", "task": "categorization reproduction", "trainingSet": "imagenet"}
                        data.update(other)
                        add_json(name, data)

                        idx += 1
                    else:
                        print(f"{name} already in json, skipping.")
    else:
        raise ValueError(f"models_file not found")


