-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:06 PM
-- Time elapsed: 8 milliseconds

local v_u_1 = {
    ["is_prod_build"] = function(_) --[[ Name: is_prod_build ]] --[[ Line: 7 ]]
        return false;
    end,
    ["get_build_time_str"] = function(_) --[[ Name: get_build_time_str ]] --[[ Line: 12 ]]
        return "====BUILD_TIME====";
    end
}
v_u_1.is_dev_build = function(_) --[[ Name: is_dev_build ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return v_u_1:is_prod_build() ~= true;
end;
return v_u_1;
