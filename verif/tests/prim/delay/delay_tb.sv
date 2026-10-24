// Maps int params (settable via -G) onto delay's type parameter.
module delay_tb
#(
  parameter int Width = 8,
  parameter int Depth = 1,
  parameter bit ResetEn = 0
)
(
  input  logic             clk,
  input  logic             rst,
  input  logic [Width-1:0] c0_data_i,
  output logic [Width-1:0] cX_data_o
);

delay #(
  .DataType(logic [Width-1:0]),
  .Depth(Depth),
  .ResetEn(ResetEn)
)
u_delay (
  .clk(clk),
  .rst(rst),
  .c0_data_i(c0_data_i),
  .cX_data_o(cX_data_o)
);

endmodule
