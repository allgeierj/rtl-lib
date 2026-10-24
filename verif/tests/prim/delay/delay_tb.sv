// Maps int params (settable via -G) onto delay's type parameter.
// ConnectRst/ConnectClkEn = 0 leave that port unconnected to exercise its default.
module delay_tb
#(
  parameter int Width = 8,
  parameter int Depth = 1,
  parameter bit ConnectRst = 1'b1,
  parameter bit ConnectClkEn = 1'b1
)
(
  input  logic             clk,
  input  logic             clk_en,
  input  logic             rst,
  input  logic [Width-1:0] c0_data_i,
  output logic [Width-1:0] cX_data_o
);

if(ConnectRst && ConnectClkEn) begin : g_dut
  delay #(.DataType(logic [Width-1:0]), .Depth(Depth))
  u_delay (.clk, .clk_en, .rst, .c0_data_i, .cX_data_o);
end else if(ConnectRst) begin : g_dut
  delay #(.DataType(logic [Width-1:0]), .Depth(Depth))
  u_delay (.clk, .rst, .c0_data_i, .cX_data_o);
end else if(ConnectClkEn) begin : g_dut
  delay #(.DataType(logic [Width-1:0]), .Depth(Depth))
  u_delay (.clk, .clk_en, .c0_data_i, .cX_data_o);
end else begin : g_dut
  delay #(.DataType(logic [Width-1:0]), .Depth(Depth))
  u_delay (.clk, .c0_data_i, .cX_data_o);
end

endmodule
