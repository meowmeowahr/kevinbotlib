# SPDX-FileCopyrightText: 2024-present Kevin Ahr <meowmeowahr@gmail.com>
#
# SPDX-License-Identifier: GPL-3.0-or-later

"""
KevinbotLib MQTT Publisher
Publish a message to a specific MQTT topic
"""

import json
import os
import re
import sys
import click
from loguru import logger

from huggingface_hub import hf_hub_url
from tqdm import tqdm
import requests
import tabulate

from kevinbotlib.speech import get_models, get_system_piper_model_dir, get_user_piper_model_dir, PiperTTSEngine


def download(url: str, output_path: str, desc="Downloading"):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    total_size = int(response.headers.get('content-length', 0))

    with tqdm(total=total_size, unit='B', unit_scale=True, desc=desc) as pbar:
        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    file.write(chunk)
                    pbar.update(len(chunk))

@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
def piper():
    """Manage the Piper TTS Engine"""

@click.group(context_settings={"help_option_names": ["-h", "--help"], "max_content_width": 120})
def models():
    """Manage neural models for Piper"""

@click.command(name="list")
@click.option("--system", is_flag=True, help="Only use global model path")
@click.option("--user", is_flag=True, help="Only use user model path")
@click.option("--raw", is_flag=True, help="Print raw json representation of installed models")
def models_list(system: bool = False, user: bool = True, raw: bool = False):
    """List the available models for Piper"""
    if not user and not system:
        user, system = True, True

    installed_models_user = get_models(user, False)
    installed_models_system = get_models(False, system)
    installed_models = get_models(user, system)

    if raw:
        print(json.dumps(installed_models, indent=4))
        return

    table = []

    for model, dir in installed_models_user.items():
        table.append([model, dir, "User"])
    for model, dir in installed_models_system.items():
        table.append([model, dir, "System"])
        
    print(tabulate.tabulate(table, headers=["Model", "Path", "Type"], tablefmt="heavy_grid"))

@click.command()
@click.argument("name")
@click.option("--system", is_flag=True, help="Use global model path")
@click.option("--user", is_flag=True, help="Use user model path")
@click.option("--repo", default="rhasspy/piper-voices", help="Huggingface Hub Repository for voice models")
def install(name: str, system: bool = False, user: bool = True, repo: str = "rhasspy/piper-voices"):
    """Install Piper model from Huggingface Hub"""
    if not re.fullmatch(r"^[a-z]{2}_[A-Z]{2}-[a-z]+-(x_low|low|medium|high)$", name):
        logger.critical(f"Model name shoud match lang_CC-voice-quality, got {name}")
        return

    locale, voice, quality = name.split('-')
    lang, region = locale.split("_")
    model_file =  f"""{name}.onnx"""
    config_file = f"""{name}.onnx.json"""

    user_inst_dir = get_user_piper_model_dir()
    system_inst_dir = get_system_piper_model_dir()

    if system:
        destn = system_inst_dir
        os.makedirs(os.path.join(destn, "models"), exist_ok=True)
    else:
        destn = user_inst_dir
        os.makedirs(destn, exist_ok=True)
        os.makedirs(os.path.join(destn, "models"), exist_ok=True)

    model_destn = os.path.join(destn, model_file)
    config_destn = os.path.join(destn, config_file)

    logger.info(f"Installing model to {model_destn}")
    logger.info(f"Installing config to {config_destn}")

    model_url = hf_hub_url(repo_id=repo,filename=f"{lang}/{locale}/{voice}/{quality}/{name}.onnx")
    config_url = hf_hub_url(repo_id=repo,filename=f"{lang}/{locale}/{voice}/{quality}/{name}.onnx.json")

    logger.debug(f"Downloading model from {model_url}")
    logger.debug(f"Downloading config from {config_url}")

    try:
        download(model_url, model_destn, "Downloading Model")
        logger.success("Model downloaded")
        download(config_url, config_destn, "Downloading Config")
        logger.success("Config downloaded")
    except KeyboardInterrupt:
        logger.warning("Download interrupted, deleting partial downloads")
        os.remove(model_destn)
        os.remove(config_destn)
        return

@click.command()
@click.argument("model")
@click.argument("text", required=False)
@click.option("--verbose", is_flag=True, help="Enable verbose output from PiperTTSEngine")
@click.option("--stdin", is_flag=True, help="Enable text input from stdin")
def synthesize(text: str | None, model: str, verbose: bool = False, stdin: bool = False):
    """Synthesize text into speech using Piper"""
    engine = PiperTTSEngine(model)
    engine.debug = verbose

    if stdin:
        engine.speak(sys.stdin.readline().strip())
        return

    if not text:
        logger.warning("No text provided")
        return

    engine.speak(text)

piper.add_command(models)
piper.add_command(synthesize)

models.add_command(install)
models.add_command(models_list)