module ram_sp
#(
  parameter type AddressType = logic [11:0],
  parameter type DataType = logic [8:0], // 4k x 9
  parameter string InitFile = "",
  parameter string RamStyle = "block" // TODO: Verify support for others
)
(
  input logic clk,
  input logic clk_en = 1'b1,
  input logic c0_wr_enable_i,
  input AddressType c0_address_i,
  input DataType c0_wr_data_i,
  output DataType c1_rd_data_o
);


  (* ram_style = RamStyle *)
  DataType memory [2**$bits(AddressType)];

  initial begin
    if(InitFile != "") begin
      $readmemh(InitFile, memory);
    end
  end

  always_ff @(posedge clk) begin
    if(clk_en) begin
      c1_rd_data_o <= memory[c0_address_i];
    end
  end

  always_ff @(posedge clk) begin
    if(clk_en && c0_wr_enable_i) begin
      memory[c0_address_i] <= c0_wr_data_i;
    end
  end

endmodule
