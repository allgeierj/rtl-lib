// Thin wrapper so Width/Stages can be set via -G; maps clk onto sync_ff's capture_clk.
module sync_ff_tb
#(
  parameter int Width = 1,
  parameter int Stages = 2
)
(
  input  logic             clk,
  input  logic [Width-1:0] c0_data_i,
  output logic [Width-1:0] cL_data_o
);

sync_ff #(.Width(Width), .Stages(Stages))
u_sync_ff (.capture_clk(clk), .c0_data_i, .cL_data_o);

endmodule
