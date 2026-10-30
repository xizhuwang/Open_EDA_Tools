`timescale 1ns/1ps
module tb_sram;
    reg clk = 0;
    always #5 clk = ~clk;
    reg en = 0, we = 0;
    reg [3:0] mask = 4'hf;
    reg [5:0] addr = 0;
    reg [31:0] wd = 0;
    wire [31:0] q1, q2, qa, qb;
    reg enb = 0, web = 0;
    reg [5:0] ab = 1;
    reg [31:0] wb = 32'hcafef00d;
    sram_1rw one (clk, en, we, mask, addr, wd, q1);
    sram_1r1w two (clk, en, addr, q2, en && we, addr, wd, mask);
    sram_2rw dual (clk, en, we, addr, wd, mask, qa, enb, web, ab, wb, 4'hf, qb);
    task check_all;
        input [31:0] value;
        begin
            if (q1 !== value || q2 !== value || qa !== value)
                $fatal(1, "SRAM expected=%h 1rw=%h 1r1w=%h 2rw=%h", value, q1, q2, qa);
        end
    endtask
    initial begin
        @(negedge clk); en = 1; we = 1; wd = 32'h12345678; enb = 1; web = 1;
        @(negedge clk); we = 0; web = 0;
        @(posedge clk); #1; check_all(32'h12345678);
        if (qb !== 32'hcafef00d) $fatal(1, "2rw independent port");
        @(negedge clk); we = 1; mask = 4'b0001; wd = 32'hdeadbeaa;
        @(posedge clk); #1; check_all(32'h12345678); // old data during write
        @(negedge clk); we = 0;
        @(posedge clk); #1; check_all(32'h123456aa);
        @(negedge clk); en = 0; addr = 5;
        @(posedge clk); #1; check_all(32'h123456aa); // disabled output holds
        $display("PASS: SRAM 1RW / 1R1W / 2RW, read-first, byte mask, hold");
        $finish;
    end
    initial begin #1000; $fatal(1, "watchdog"); end
endmodule
