// Original model: independent 1R + 1W ports, one common clock, read-first.
`default_nettype none
module sram_1r1w #(
    parameter ADDR_WIDTH = 6,
    parameter DATA_WIDTH = 32
) (
    input wire clk,
    input wire ren,
    input wire [ADDR_WIDTH-1:0] raddr,
    output reg [DATA_WIDTH-1:0] rdata,
    input wire wen,
    input wire [ADDR_WIDTH-1:0] waddr,
    input wire [DATA_WIDTH-1:0] wdata,
    input wire [DATA_WIDTH/8-1:0] byte_en
);
    reg [DATA_WIDTH-1:0] mem [0:(1<<ADDR_WIDTH)-1];
    integer b;
    always @(posedge clk) begin
        if (ren) rdata <= mem[raddr];
        if (wen)
            for (b = 0; b < DATA_WIDTH/8; b = b + 1)
                if (byte_en[b]) mem[waddr][b*8 +: 8] <= wdata[b*8 +: 8];
    end
endmodule
`default_nettype wire
