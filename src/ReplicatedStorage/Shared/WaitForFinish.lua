-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:09 PM
-- Cached decompilation

local v_u_4 = {
    ["new"] = function(_, p_u_1, p_u_2) --[[ Name: new ]] --[[ Line: 3 ]]
        local v3 = {}
        v3.finish = function(_) --[[ Name: finish ]] --[[ Line: 6 ]]
            --[[ Upvalues: (ref 1): p_u_1, (copy 2): p_u_2 ]]
            p_u_1 = p_u_1 - 1
            if p_u_1 == 0 then
                p_u_2()
            end;
        end;
        return v3;
    end,
    ["Builder"] = {}
}
v_u_4.Builder.new = function(_) --[[ Name: new ]] --[[ Line: 30 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    local v5 = {}
    local v_u_6 = 0
    local v_u_7 = nil
    v5.begin = function(_) --[[ Name: begin ]] --[[ Line: 36 ]]
        --[[ Upvalues: (ref 1): v_u_6 ]]
        v_u_6 = v_u_6 + 1
    end;
    v5.finish = function(_) --[[ Name: finish ]] --[[ Line: 40 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_6 ]]
        if v_u_7 == nil then
            v_u_6 = v_u_6 - 1
        else
            v_u_7:finish()
        end;
    end;
    v5.wait_for_finish = function(_, p8) --[[ Name: wait_for_finish ]] --[[ Line: 48 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (ref 3): v_u_6 ]]
        if v_u_7 == nil then
            v_u_7 = v_u_4:new(v_u_6, p8)
            if v_u_6 == 0 then
                p8()
            end;
        end;
        return v_u_7;
    end;
    return v5;
end;
return v_u_4;
