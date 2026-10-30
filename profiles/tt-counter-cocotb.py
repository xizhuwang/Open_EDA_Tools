# Copyright (c) 2026 Xi-Zhu Wang — MIT.
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer


@cocotb.test()
async def counter_behavior(dut):
    dut.rst_n.value = 0
    dut.ena.value = 1
    dut.ui_in.value = 0
    dut.uio_in.value = 0
    cocotb.start_soon(Clock(dut.clk, 20, unit='ns').start())
    await ClockCycles(dut.clk, 5)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    expected = 0
    for i in range(600):
        enabled = i % 9 != 0
        control = 2 if i == 320 else (1 if i % 5 != 0 else 0)
        dut.ena.value = int(enabled)
        dut.ui_in.value = control
        await RisingEdge(dut.clk)
        if enabled:
            expected = 0 if control & 2 else ((expected + 1) & 255 if control & 1 else expected)
        await Timer(5, unit='ns')
        assert int(dut.uo_out.value) == expected, f'cycle {i}: expected {expected}, actual {dut.uo_out.value}'
        assert int(dut.uio_oe.value) == 0
        assert int(dut.uio_out.value) == 0
        await FallingEdge(dut.clk)
