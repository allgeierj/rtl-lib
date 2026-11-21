// Maps int params (settable via -G) onto ram_sp's type parameters.
// ConnectClkEn = 0 leaves clk_en unconnected to exercise its default.
// UseInitFile = 1 loads RAM_SP_INIT_FILE (set in config.mk with an absolute path).
`ifndef RAM_SP_INIT_FILE
`define RAM_SP_INIT_FILE ""
`endif
module ram_sp_tb
#(
  parameter int AddrWidth = 12,
  parameter int Width = 9,
  parameter bit OutputReg = 1'b0,
  parameter bit ConnectClkEn = 1'b1,
  parameter bit UseInitFile = 1'b0
)
(
  input  logic                 clk,
  input  logic                 clk_en,
  input  logic                 c0_wr_enable_i,
  input  logic [AddrWidth-1:0] c0_address_i,
  input  logic [Width-1:0]     c0_wr_data_i,
  output logic [Width-1:0]     cL_rd_data_o
);

localparam string InitFile = UseInitFile ? `RAM_SP_INIT_FILE : "";

if(ConnectClkEn) begin : g_dut
  ram_sp #(.AddressType(logic [AddrWidth-1:0]), .DataType(logic [Width-1:0]), .OutputReg(OutputReg), .InitFile(InitFile))
  u_ram_sp (.clk, .clk_en, .c0_wr_enable_i, .c0_address_i, .c0_wr_data_i, .cL_rd_data_o);
end else begin : g_dut
  ram_sp #(.AddressType(logic [AddrWidth-1:0]), .DataType(logic [Width-1:0]), .OutputReg(OutputReg), .InitFile(InitFile))
  u_ram_sp (.clk, .c0_wr_enable_i, .c0_address_i, .c0_wr_data_i, .cL_rd_data_o);
end

endmodule
