// Original model: two read/write ports, common clock, read-first.
// Simultaneous writes to the same address are prohibited, even disjoint lanes.
`default_nettype none
module sram_2rw #(
    parameter ADDR_WIDTH = 6,
    parameter DATA_WIDTH = 32
) (
    input wire clk,
    input wire en_a,
    input wire we_a,
    input wire [ADDR_WIDTH-1:0] addr_a,
    input wire [DATA_WIDTH-1:0] wdata_a,
    input wire [DATA_WIDTH/8-1:0] byte_en_a,
    output reg [DATA_WIDTH-1:0] rdata_a,
    input wire en_b,
    input wire we_b,
    input wire [ADDR_WIDTH-1:0] addr_b,
    input wire [DATA_WIDTH-1:0] wdata_b,
    input wire [DATA_WIDTH/8-1:0] byte_en_b,
    output reg [DATA_WIDTH-1:0] rdata_b
);
    reg [DATA_WIDTH-1:0] mem [0:(1<<ADDR_WIDTH)-1];
    integer b;
    always @(posedge clk) begin
        if (en_a) rdata_a <= mem[addr_a];
        if (en_b) rdata_b <= mem[addr_b];
        if (en_a && we_a)
            for (b = 0; b < DATA_WIDTH/8; b = b + 1)
                if (byte_en_a[b]) mem[addr_a][b*8 +: 8] <= wdata_a[b*8 +: 8];
        if (en_b && we_b)
            for (b = 0; b < DATA_WIDTH/8; b = b + 1)
                if (byte_en_b[b]) mem[addr_b][b*8 +: 8] <= wdata_b[b*8 +: 8];
        // synthesis translate_off
        if (en_a && we_a && en_b && we_b && addr_a == addr_b)
            $fatal(1, "sram_2rw: same-address simultaneous write is illegal");
        // synthesis translate_on
    end
endmodule
`default_nettype wire
