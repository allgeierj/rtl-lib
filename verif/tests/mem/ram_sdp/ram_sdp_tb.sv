// Maps int params (settable via -G) onto ram_sdp's type parameters.
// SharedClock = 1 clocks both ports from rd_clk, leaving the wr_clk pin unused.
// ConnectClkEn = 0 leaves rd_clk_en and wr_clk_en unconnected to exercise their defaults.
// UseInitFile = 1 loads RAM_SDP_INIT_FILE (set in config.mk with an absolute path).
`ifndef RAM_SDP_INIT_FILE
`define RAM_SDP_INIT_FILE ""
`endif
module ram_sdp_tb
#(
  parameter int AddrWidth = 12,
  parameter int Width = 9,
  parameter bit OutputReg = 1'b0,
  parameter bit SharedClock = 1'b0,
  parameter bit ConnectClkEn = 1'b1,
  parameter bit UseInitFile = 1'b0
)
(
  input  logic                 rd_clk,
  input  logic                 rd_clk_en,
  input  logic                 rd_c0_enable_i,
  input  logic [AddrWidth-1:0] rd_c0_address_i,
  output logic [Width-1:0]     rd_cL_data_o,
  input  logic                 wr_clk,
  input  logic                 wr_clk_en,
  input  logic                 wr_c0_enable_i,
  input  logic [AddrWidth-1:0] wr_c0_address_i,
  input  logic [Width-1:0]     wr_c0_data_i
);

localparam string InitFile = UseInitFile ? `RAM_SDP_INIT_FILE : "";

if(ConnectClkEn) begin : g_dut
  ram_sdp #(.AddressType(logic [AddrWidth-1:0]), .DataType(logic [Width-1:0]), .OutputReg(OutputReg), .InitFile(InitFile))
  u_ram_sdp (.rd_clk, .rd_clk_en, .rd_c0_enable_i, .rd_c0_address_i, .rd_cL_data_o,
             .wr_clk(SharedClock ? rd_clk : wr_clk), .wr_clk_en, .wr_c0_enable_i, .wr_c0_address_i, .wr_c0_data_i);
end else begin : g_dut
  ram_sdp #(.AddressType(logic [AddrWidth-1:0]), .DataType(logic [Width-1:0]), .OutputReg(OutputReg), .InitFile(InitFile))
  u_ram_sdp (.rd_clk, .rd_c0_enable_i, .rd_c0_address_i, .rd_cL_data_o,
             .wr_clk(SharedClock ? rd_clk : wr_clk), .wr_c0_enable_i, .wr_c0_address_i, .wr_c0_data_i);
end

endmodule
