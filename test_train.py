from pathlib import Path
from encoder.data_objects import SpeakerVerificationDataLoader, SpeakerVerificationDataset
from encoder.params_model import speakers_per_batch, utterances_per_speaker, learning_rate_init
import time

def train(run_id: str, clean_data_root: Path):
    # Create a dataset and a dataloader
    dataset = SpeakerVerificationDataset(clean_data_root, max_samples=speakers_per_batch*500 + 1)
    loader = SpeakerVerificationDataLoader(
        dataset,
        speakers_per_batch,
        utterances_per_speaker,
        num_workers=4,
    )
    init_step = 1
    
    print("start loop")
    counter = 0
    steps = dict()
    start_time = time.time()  # Get the start time
    total_elapsed_time = 0
    for step, speaker_batch in enumerate(loader, init_step):
        counter += 1
        if counter < 20:
        # steps.update( {step: steps.get(step, 0) + 1} )
            continue
        if counter % 20 == 0:
            elapsed_time = time.time() - start_time
            total_elapsed_time += elapsed_time  # Accumulate total elapsed time

            print(f"Iteration {counter=}, {len(steps)=}, Elapsed Time: {elapsed_time:.2f} seconds")
            start_time = time.time()  # Reset the start ti

            if counter % 40 == 0:  # Print average every 20 iterations
                average_time = 20 * (total_elapsed_time / counter)
                print(f"Average Time all Iterations: {average_time:.2f} seconds")


    print(f"finished. {counter=}")

train("S", Path("/mnt/c/Users/ssch7/repos/Real-Time-Voice-Cloning/datasets/SV2TTS/encoder"))


"""
# utterances preloaded
3.03 at 880
2.59 at 780

# baseline
38.01 at 40

"""