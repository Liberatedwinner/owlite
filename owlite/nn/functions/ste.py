# pylint: disable=duplicate-code, unused-argument
from typing import Any, Optional

import torch
from torch import Tensor
from torch.autograd import Function

from .fake_quantize import fake_quantize


# mypy: disable-error-code=override
# pylint: disable-next=abstract-method
class STEFunction(Function):
    """fake quantizing function for QAT using STE (Straight-Through Estimator)

    For quant_min <= input <= quant_max the gradient passes straight through,
    otherwise the gradient is zero
    """

    @staticmethod  # pylint: disable-next=arguments-differ
    def forward(
        ctx: Any,
        inputs: Tensor,
        step_size: Tensor,
        zero_point: Tensor,
        grad_scale: float,  # grad_scale is not used
        quant_min: int,
        quant_max: int,
        axis: Optional[int],
        compensate_zp: bool,  # compensate_zp is not used
    ) -> Tensor:
        """grad_scale and compensate_zp are unused arguments in symmetric quantization"""
        ctx.save_for_backward(inputs)
        lower_bound = quant_min * step_size
        upper_bound = quant_max * step_size
        ctx.other = lower_bound, upper_bound
        return fake_quantize(inputs, step_size, zero_point, quant_min, quant_max, axis)

    @staticmethod
    def backward(ctx: Any, *grad_outputs: Any) -> Any:
        inputs = ctx.saved_tensors[0]
        grad_output = grad_outputs[0]
        lower_bound, upper_bound = ctx.other
        lower_bound = lower_bound.reshape([-1] + ([1] * (inputs.dim() - 1)))
        upper_bound = lower_bound.reshape([-1] + ([1] * (inputs.dim() - 1)))
        grad_inputs = torch.where(inputs.ge(lower_bound) * inputs.le(upper_bound), grad_output, 0)
        return grad_inputs, None, None, None, None, None, None, None


ste_function = STEFunction.apply
