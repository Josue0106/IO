from core.data_model import load_case
from optimization import pulp_model as pm
import inspect
print('module file:', pm.__file__)
src = inspect.getsource(pm)
print('\n'.join(src.splitlines()[-60:]))
