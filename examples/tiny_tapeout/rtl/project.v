// Copyright (c) 2026 Xi-Zhu Wang — MIT.
`default_nettype none
module tt_um_openeda_counter (
    input  wire [7:0] ui_in,
    output wire [7:0] uo_out,
    input  wire [7:0] uio_in,
    output wire [7:0] uio_out,
    output wire [7:0] uio_oe,
    input  wire       ena,
    input  wire       clk,
    input  wire       rst_n
);
    reg [7:0] count;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) count <= 8'h00;
        else if (ena) begin
            if (ui_in[1]) count <= 8'h00;
            else if (ui_in[0]) count <= count + 8'h01;
        end
    end
    assign uo_out = count;
    // Never drive the bidirectional pins in this example.
    assign uio_out = 8'h00;
    assign uio_oe = 8'h00;
    wire _unused = &{ui_in[7:2], uio_in, 1'b0};
endmodule
`default_nettype wire
