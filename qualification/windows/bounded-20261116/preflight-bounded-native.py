import json,sys
from pathlib import Path
root=Path('/home/nvidia/b12x-flare')
sys.path.insert(0,str(root/'scripts'))
from flare_candidate import RECIPE,load_recipe
from flare_run import serving_recipe,serving_command
rank=int(sys.argv[1]);recipe=serving_recipe(load_recipe(RECIPE))
recipe.update(native_arm=sys.argv[2],scheduler_policy='balanced',scheduler_trace='off')
state=json.loads((root/'local/accepted-core.json').read_text())
command=serving_command(recipe,rank,state)
assert '--scheduler-policy' in command and command[command.index('--scheduler-policy')+1]=='balanced'
print(json.dumps({'rank':rank,'command_and_provenance_preflight':'passed','manifest':recipe['native_arm']}))
