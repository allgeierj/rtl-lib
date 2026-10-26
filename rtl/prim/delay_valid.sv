// Delays valid and data together by Depth enabled cycles (combinational when Depth == 0).
// rst clears only valid, so the data line still maps to SRLs.
module delay_valid
#(
  parameter type DataType = logic,
  parameter int Depth = 1
)
(
  input logic clk,
  input logic clk_en = 1'b1,
  input logic rst = 1'b0,
  input logic c0_valid_i,
  input DataType c0_data_i,
  output logic cX_valid_o,
  output DataType cX_data_o
);

delay #(
  .DataType(logic),
  .Depth(Depth)
)
valid_delay (
  .clk(clk),
  .clk_en(clk_en),
  .rst(rst),
  .c0_data_i(c0_valid_i),
  .cX_data_o(cX_valid_o)
);

delay #(
  .DataType(DataType),
  .Depth(Depth)
)
data_delay (
  .clk(clk),
  .clk_en(clk_en),
  .c0_data_i(c0_data_i),
  .cX_data_o(cX_data_o)
);

endmodule
