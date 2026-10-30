`timescale 1ns/1ps
module tb;
    reg clk = 0;
    reg rst_n = 0;
    reg ena = 1;
    reg [7:0] ui_in = 0;
    wire [7:0] uo_out, uio_out, uio_oe;
    reg [7:0] expected = 0;
    integer i;
    tt_um_openeda_counter dut (.clk(clk), .rst_n(rst_n), .ena(ena), .ui_in(ui_in),
        .uio_in(8'h00), .uo_out(uo_out), .uio_out(uio_out), .uio_oe(uio_oe));
    always #10 clk = ~clk;
    initial begin
        $dumpfile("dump.vcd"); $dumpvars(0, tb);
        repeat (2) @(negedge clk);
        rst_n = 1;
        for (i = 0; i < 600; i = i + 1) begin
            ena = (i % 9 != 0);
            ui_in = (i == 320) ? 8'h02 : ((i % 5 != 0) ? 8'h01 : 8'h00);
            @(posedge clk);
            if (ena) begin
                if (ui_in[1]) expected = 0;
                else if (ui_in[0]) expected = expected + 8'h01;
            end
            #5;
            if (uo_out !== expected) $fatal(1, "TT cycle=%0d expected=%h actual=%h", i, expected, uo_out);
            if (uio_oe !== 0 || uio_out !== 0) $fatal(1, "Unexpected bidirectional drive");
            @(negedge clk);
        end
        $display("PASS: Tiny Tapeout counter 600 cycles, stall, enable, clear, wrap and safe IO");
        $finish;
    end
    initial begin #20000; $fatal(1, "watchdog"); end
endmodule
