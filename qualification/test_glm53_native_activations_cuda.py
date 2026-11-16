"""The supported native-dense-activations option, with unchanged KDA bounds.

The original auto-precision control is retained in test_glm53_state_cuda.py and
has two failed receipts. This arm changes only the preparation-session option.
It does not alter the serving core, source pins, stored weights or MoE precision.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(os.environ.get("FLARE_RUN_CUDA_TESTS") != "1",
                               reason="requires an explicitly assigned CUDA device")


@pytest.mark.parametrize("world,verify_width", [(2, 4), (4, 6)])
def test_native_dense_kda_prefix(world, verify_width, record_property):
    from test_glm53_state_cuda import test_learned_kda_verification_commits_each_prefix_before_plain_decode

    test_learned_kda_verification_commits_each_prefix_before_plain_decode(
        world, verify_width, record_property, native_dense_activations=True)
