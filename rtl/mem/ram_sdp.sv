// Simple dual-port RAM: writes on wr_clk, reads on rd_clk. Read latency is 1 rd_clk cycle, or 2
// with OutputReg. With rd_c0_enable_i low, rd_cL_data_o keeps the last word read. rd_clk_en low
// holds the read pipeline; wr_clk_en low blocks writes. Reading the address being written returns
// the old word when both ports share a clock, and is undefined with separate clocks. Separate
// clocks rule out URAM, and distributed RAM then needs a wr_clk -> rd_clk timing constraint.
// Words are X until written unless InitFile ($readmemh hex) is set; rd_cL_data_o is X until the
// first read.
module ram_sdp
#(
  parameter type AddressType = logic [11:0],
  parameter type DataType = logic [8:0], // 4k x 9
  parameter bit OutputReg = 1'b0,
  parameter string InitFile = "",
  parameter RamStyle = "block",
  localparam int Latency = 1 + OutputReg
)
(
  input logic rd_clk,
  input logic rd_clk_en = 1'b1,
  input logic rd_c0_enable_i,
  input AddressType rd_c0_address_i,
  output DataType rd_cL_data_o,
  input logic wr_clk,
  input logic wr_clk_en = 1'b1,
  input logic wr_c0_enable_i,
  input AddressType wr_c0_address_i,
  input DataType wr_c0_data_i
);

  (* ram_style = RamStyle *)
  DataType memory [2**$bits(AddressType)];
  DataType rd_c1_data;

  initial begin
    if(InitFile != "") begin
      $readmemh(InitFile, memory);
    end
  end

  always_ff @(posedge rd_clk) begin
    if(rd_clk_en && rd_c0_enable_i) begin
      rd_c1_data <= memory[rd_c0_address_i];
    end
  end

  always_ff @(posedge wr_clk) begin
    if(wr_clk_en && wr_c0_enable_i) begin
      memory[wr_c0_address_i] <= wr_c0_data_i;
    end
  end

  if(OutputReg) begin
    always_ff @(posedge rd_clk) begin
      if(rd_clk_en) begin
        rd_cL_data_o <= rd_c1_data;
      end
    end
  end
  else begin
    assign rd_cL_data_o = rd_c1_data;
  end

endmodule
