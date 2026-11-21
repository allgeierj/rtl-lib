// Single-port RAM, read-first: reading the address being written returns the old word.
// Read latency is 1, or 2 with OutputReg, which maps onto the RAM primitive's output register
// (BRAM DOA_REG, URAM OREG). clk_en low blocks writes and holds the read pipeline. Words are X
// until written unless InitFile ($readmemh hex) is set; cL_rd_data_o is X until the first read.
module ram_sp
#(
  parameter type AddressType = logic [11:0],
  parameter type DataType = logic [8:0], // 4k x 9
  parameter bit OutputReg = 1'b0,
  parameter string InitFile = "",
  parameter RamStyle = "block",
  localparam int Latency = 1 + OutputReg
)
(
  input logic clk,
  input logic clk_en = 1'b1,
  input logic c0_wr_enable_i,
  input AddressType c0_address_i,
  input DataType c0_wr_data_i,
  output DataType cL_rd_data_o
);

  (* ram_style = RamStyle *)
  DataType memory [2**$bits(AddressType)];
  DataType c1_rd_data;

  initial begin
    if(InitFile != "") begin
      $readmemh(InitFile, memory);
    end
  end

  always_ff @(posedge clk) begin
    if(clk_en) begin
      c1_rd_data <= memory[c0_address_i];
    end
  end

  always_ff @(posedge clk) begin
    if(clk_en && c0_wr_enable_i) begin
      memory[c0_address_i] <= c0_wr_data_i;
    end
  end

  if(OutputReg) begin
    always_ff @(posedge clk) begin
      if(clk_en) begin
        cL_rd_data_o <= c1_rd_data;
      end
    end
  end
  else begin
    assign cL_rd_data_o = c1_rd_data;
  end

endmodule
