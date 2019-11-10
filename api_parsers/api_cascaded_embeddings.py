#! /usr/bin/env python3

import torch

import architectures as arch
from .api_train_with_classifier import APIMaybeExtendTrainWithClassifier
import numpy as np
from utils import common_functions as c_f
from pytorch_metric_learning.utils import common_functions as pml_c_f

class APICascadedEmbeddings(APIMaybeExtendTrainWithClassifier):
    def get_trainer_kwargs(self):
        trainer_kwargs = self.inheriter.get_trainer_kwargs()
        trainer_kwargs["embedding_sizes"] = self.all_embedding_sizes
        return trainer_kwargs

    def get_embedder_model(self, model_type, input_size=None, output_size=None):
        embedders = []
        for i in input_size:
            embedders.append(self.inheriter.get_embedder_model(model_type, input_size=i, output_size=output_size))
        self.all_embedding_sizes = [c_f.get_last_linear(embedders[0]).out_features] * len(embedders)
        model = arch.misc_models.ListOfModels(embedders, input_size)
        return model

    def get_trunk_model(self, model_type, force_pretrained=False):
        self.models["trunk"] = self.inheriter.get_trunk_model(model_type, force_pretrained=force_pretrained)
        self.set_transforms()
        self.set_transforms = lambda: None
        sample_input = pml_c_f.try_keys(self.dataset[0], ["data", "image"]).unsqueeze(0)
        (model_name, _), = model_type.items()
        model = arch.misc_models.LayerExtractor(
            self.models["trunk"],
            self.args.layers_to_extract,
            self.get_skip_layer_names(model_name),
            self.get_insert_functions(model_name),
        )
        _, self.base_model_output_size = model.layer_by_layer(sample_input, return_layer_sizes=True)
        return model

    def get_skip_layer_names(self, model_name):
        return {"inception_v3": "AuxLogits"}[model_name]

    def get_insert_functions(self, model_name):
        return {
            "inception_v3": {
                "Conv2d_2b_3x3": [torch.nn.MaxPool2d(3, stride=2)],
                "Conv2d_4a_3x3": [torch.nn.MaxPool2d(3, stride=2)],
            }
        }[model_name]