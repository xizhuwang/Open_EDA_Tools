`timescale 1ns/1ps
`default_nettype none
module tb;
    reg clk = 0;
    reg rst_n = 0;
    reg enable = 0;
    wire [7:0] count;
    reg [7:0] expected = 0;
    integer i;
    counter dut (.clk(clk), .rst_n(rst_n), .enable(enable), .count(count));
    always #10 clk = ~clk;
    initial begin
        $dumpfile("dump.vcd");
        $dumpvars(0, tb);
        repeat (2) @(negedge clk);
        rst_n = 1;
        for (i = 0; i < 300; i = i + 1) begin
            enable = (i % 5 != 0);
            @(posedge clk);
            if (enable) expected = expected + 8'h01;
            #1;
            if (count !== expected)
                $fatal(1, "cycle=%0d expected=%h actual=%h", i, expected, count);
            @(negedge clk);
        end
        rst_n = 0;
        #1;
        if (count !== 8'h00) $fatal(1, "async reset failed");
        $display("PASS: counter 300 cycles, stalls, wrap and reset");
        $finish;
    end
    initial begin
        #20000;
        $fatal(1, "simulation watchdog");
    end
endmodule
`default_nettype wire
