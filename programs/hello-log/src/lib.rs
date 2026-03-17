use solana_program::{
    account_info::AccountInfo, entrypoint, entrypoint::ProgramResult, msg, pubkey::Pubkey,
};

entrypoint!(process_instruction);

fn process_instruction(
    program_id: &Pubkey,
    _accounts: &[AccountInfo],
    instruction_data: &[u8],
) -> ProgramResult {
    msg!("hello-log: program_id={}", program_id);
    if instruction_data.is_empty() {
        msg!("hello-log: no data");
    } else {
        msg!(
            "hello-log: data_len={} first_byte={}",
            instruction_data.len(),
            instruction_data[0]
        );
    }
    msg!("hello-log: success");
    Ok(())
}
