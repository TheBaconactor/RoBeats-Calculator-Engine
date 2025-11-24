-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:02 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local s_HttpService_0 = game:GetService("HttpService")
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v3 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_4 = nil
v3:require_client(function() --[[ Line: 6 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    v_u_4 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
end)
local v8 = {
    ["create_error_menu"] = function(_, p5, p6, p7) --[[ Name: create_error_menu ]] --[[ Line: 40 ]]
        --[[ Upvalues: (ref 1): v_u_4 ]]
        return v_u_4:new(p5, p6, p7):set_text("Disabled", "Because of restrictions in your country, this functionality has been disabled.");
    end
}
local v_u_9 = true
local v_u_10 = true
v8.client_init = function(_) --[[ Name: client_init ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_9, (ref 3): v_u_10, (copy 4): v_u_1, (copy 5): s_HttpService_0 ]]
    spawn(function() --[[ Line: 16 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_9, (ref 3): v_u_10, (ref 4): v_u_1, (ref 5): s_HttpService_0 ]]
        while game.Players.LocalPlayer == nil do
            wait(0.1)
        end;
        local v11 = game:GetService("PolicyService"):GetPolicyInfoForPlayerAsync(game.Players.LocalPlayer)
        if v_u_2.ForceDisablePaidItemPlayerPolicy == true then
            v_u_9 = false
            v_u_10 = false
            v_u_1:warnf("DebugConfig.ForceDisablePaidItemPlayerPolicy enabled")
        else
            if typeof(v11.ArePaidRandomItemsRestricted) == "boolean" then
                v_u_9 = not v11.ArePaidRandomItemsRestricted
            end;
            if typeof(v11.IsPaidItemTradingAllowed) == "boolean" then
                v_u_10 = v11.IsPaidItemTradingAllowed
            end;
        end;
        v_u_1:puts("Local Player PolicyInfo (%s)", s_HttpService_0:JSONEncode(v11))
    end)
end;
v8.has_any_paid_item_restrictions = function(_) --[[ Name: has_any_paid_item_restrictions ]] --[[ Line: 38 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10 ]]
    return v_u_9 ~= true and true or v_u_10 ~= true;
end;
return v8;
