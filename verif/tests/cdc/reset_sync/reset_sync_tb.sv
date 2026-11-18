// Thin wrapper so Stages can be set via -G.
module reset_sync_tb
#(
  parameter int Stages = 2
)
(
  input  logic clk,
  input  logic async_rst_i,
  output logic rst_o
);

reset_sync #(.Stages(Stages))
u_reset_sync (.clk, .async_rst_i, .rst_o);

endmodule
