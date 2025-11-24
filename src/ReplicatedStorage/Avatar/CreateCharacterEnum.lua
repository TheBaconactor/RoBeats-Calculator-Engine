-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:17 PM
-- Cached decompilation

local v_u_1 = Enum
local v_u_2 = {
    ["AvatarTypes"] = {
        ["R6"] = 0,
        ["R15"] = 1,
        ["Unknown"] = 2
    }
}
local v_u_3 = {}
GetProxyForEnum = function(p4) --[[ Name: GetProxyForEnum ]] --[[ Line: 17 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2 ]]
    if not v_u_3[p4] then
        local v5 = v_u_3
        local v6 = {
            ["__newindex"] = function(_, _, _) --[[ Name: __newindex ]] --[[ Line: 31 ]]
                error("You can not add EnumItems at run time!")
            end
        }
        v6.__index = function(p7, p8) --[[ Name: __index ]] --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_2 ]]
            if v_u_2[p7.EnumName][p8] == nil then
                error(string.format("EnumItem %s does not exist!", p8))
            end;
            return v_u_2[p7.EnumName][p8];
        end;
        v5[p4] = setmetatable({
            ["EnumName"] = p4
        }, v6)
    end;
    return v_u_3[p4];
end;
return setmetatable({}, {
    ["__index"] = function(_, p9) --[[ Name: __index ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        if v_u_2[p9] == nil then
            return v_u_1[p9];
        else
            return GetProxyForEnum(p9);
        end;
    end,
    ["__newindex"] = function(_, _, _) --[[ Name: __newindex ]] --[[ Line: 50 ]]
        error("You can not add Enums at run time!")
    end
});
