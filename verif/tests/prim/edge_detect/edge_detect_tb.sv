// ConnectRst/ConnectClkEn = 0 leave that port unconnected to exercise its default.
module edge_detect_tb
#(
  parameter int Width = 8,
  parameter bit ConnectRst = 1'b1,
  parameter bit ConnectClkEn = 1'b1
)
(
  input  logic             clk,
  input  logic             clk_en,
  input  logic             rst,
  input  logic [Width-1:0] c0_detect_i,
  output logic             c0_valid_o,
  output logic [Width-1:0] c0_rising_o,
  output logic [Width-1:0] c0_falling_o,
  output logic [Width-1:0] c0_either_o
);

if(ConnectRst && ConnectClkEn) begin : g_dut
  edge_detect #(.Width(Width))
  u_edge_detect (.clk, .clk_en, .rst, .c0_detect_i, .c0_valid_o, .c0_rising_o, .c0_falling_o, .c0_either_o);
end else if(ConnectRst) begin : g_dut
  edge_detect #(.Width(Width))
  u_edge_detect (.clk, .rst, .c0_detect_i, .c0_valid_o, .c0_rising_o, .c0_falling_o, .c0_either_o);
end else if(ConnectClkEn) begin : g_dut
  edge_detect #(.Width(Width))
  u_edge_detect (.clk, .clk_en, .c0_detect_i, .c0_valid_o, .c0_rising_o, .c0_falling_o, .c0_either_o);
end else begin : g_dut
  edge_detect #(.Width(Width))
  u_edge_detect (.clk, .c0_detect_i, .c0_valid_o, .c0_rising_o, .c0_falling_o, .c0_either_o);
end

endmodule
