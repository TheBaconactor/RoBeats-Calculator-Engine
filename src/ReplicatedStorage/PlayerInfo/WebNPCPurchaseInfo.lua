-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v4 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = {
    ["Tiers"] = {
        ["Tier1"] = 1,
        ["Tier2"] = 2,
        ["Tier3"] = 3
    },
    ["SELECTED_DANCE_RANDOM"] = 0,
    ["NPCData"] = {}
}
local v_u_7 = v_u_5:new({ v_u_6.Tiers.Tier1, v_u_6.Tiers.Tier2, v_u_6.Tiers.Tier3 })
v_u_6.all_tiers_list = function(_) --[[ Name: all_tiers_list ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_7 ]]
    return v_u_7;
end;
v_u_6.tier_get_price_type_and_amount = function(_, p8) --[[ Name: tier_get_price_type_and_amount ]] --[[ Line: 23 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_1, (copy 3): v_u_2 ]]
    if p8 == v_u_6.Tiers.Tier1 then
        return v_u_1.CurrencyType.Coins, 1000;
    end;
    if p8 == v_u_6.Tiers.Tier2 then
        return v_u_1.CurrencyType.Stars, 10;
    end;
    if p8 == v_u_6.Tiers.Tier3 then
        return v_u_1.CurrencyType.Stars, 50;
    end;
    v_u_2:errf("WebNPCPurchaseInfo:tier_get_price_type_and_amount invalid tier(%s)", (tostring(p8)))
end;
v_u_6.tier_to_emoji = function(_, p9) --[[ Name: tier_to_emoji ]] --[[ Line: 38 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    return p9 == v_u_6.Tiers.Tier1 and "1\239\184\143\226\131\163" or (p9 == v_u_6.Tiers.Tier2 and "2\239\184\143\226\131\163" or (p9 == v_u_6.Tiers.Tier3 and "3\239\184\143\226\131\163" or "\226\157\147"));
end;
local v_u_10 = v_u_5:new():push_back_table_list({ v4.RewardInfo:new(v4.RewardType.Coins, 50, -1) })
local v_u_11 = v_u_5:new():push_back_table_list({ v4.RewardInfo:new(v4.RewardType.Stars, 1, -1) })
v_u_6.tier_visit_reward_desc_info_list = function(_, p12) --[[ Name: tier_visit_reward_desc_info_list ]] --[[ Line: 59 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_10, (copy 3): v_u_11, (copy 4): v_u_2 ]]
    if p12 == v_u_6.Tiers.Tier2 then
        return v_u_10;
    end;
    if p12 == v_u_6.Tiers.Tier3 then
        return v_u_11;
    end;
    v_u_2:errf("WebNPCPurchaseInfo:tier_visit_reward_type_and_amount invalid tier(%s)", (tostring(p12)))
end;
v_u_6.NPCData.new = function(_, p_u_13, p_u_14, p_u_15, p_u_16, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 74 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_6 ]]
    v_u_3:is_int(p_u_13)
    v_u_3:is_string(p_u_14)
    v_u_3:is_int(p_u_15)
    v_u_3:is_string(p_u_16)
    v_u_3:is_enum_member(p_u_17, v_u_6.Tiers)
    v_u_3:is_string(p_u_18)
    v_u_3:is_int(p_u_19)
    local v20 = {}
    local v_u_21 = os.time()
    local v_u_22 = 0
    local v_u_23 = 0
    local v_u_24 = false
    v20.get_webnpcid = function(_) --[[ Name: get_webnpcid ]] --[[ Line: 90 ]]
        --[[ Upvalues: (copy 1): p_u_13 ]]
        return p_u_13;
    end;
    v20.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 91 ]]
        --[[ Upvalues: (copy 1): p_u_14 ]]
        return p_u_14;
    end;
    v20.get_userid = function(_) --[[ Name: get_userid ]] --[[ Line: 92 ]]
        --[[ Upvalues: (copy 1): p_u_15 ]]
        return p_u_15;
    end;
    v20.get_message = function(_) --[[ Name: get_message ]] --[[ Line: 93 ]]
        --[[ Upvalues: (copy 1): p_u_16 ]]
        return p_u_16;
    end;
    v20.get_tier = function(_) --[[ Name: get_tier ]] --[[ Line: 94 ]]
        --[[ Upvalues: (copy 1): p_u_17 ]]
        return p_u_17;
    end;
    v20.get_anchor = function(_) --[[ Name: get_anchor ]] --[[ Line: 95 ]]
        --[[ Upvalues: (ref 1): p_u_18 ]]
        return p_u_18;
    end;
    v20.get_danceid = function(_) --[[ Name: get_danceid ]] --[[ Line: 96 ]]
        --[[ Upvalues: (ref 1): p_u_19 ]]
        return p_u_19;
    end;
    v20.set_anchor = function(p25, p26) --[[ Name: set_anchor ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_18 ]]
        v_u_3:is_string(p26)
        p_u_18 = p26
        return p25;
    end;
    v20.set_danceid = function(p27, p28) --[[ Name: set_danceid ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_19 ]]
        v_u_3:is_int(p28)
        p_u_19 = p28
        return p27;
    end;
    v20.set_created_at = function(p29, p30) --[[ Name: set_created_at ]] --[[ Line: 110 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_21 ]]
        v_u_3:is_int(p30)
        v_u_21 = p30
        return p29;
    end;
    v20.set_like_count = function(p31, p32) --[[ Name: set_like_count ]] --[[ Line: 111 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_22 ]]
        v_u_3:is_int(p32)
        v_u_22 = p32
        return p31;
    end;
    v20.set_comment_count = function(p33, p34) --[[ Name: set_comment_count ]] --[[ Line: 112 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_23 ]]
        v_u_3:is_int(p34)
        v_u_23 = p34
        return p33;
    end;
    v20.set_disable_comments = function(p35, p36) --[[ Name: set_disable_comments ]] --[[ Line: 113 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_24 ]]
        v_u_3:is_bool(p36)
        v_u_24 = p36
        return p35;
    end;
    v20.get_created_at = function(_) --[[ Name: get_created_at ]] --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21;
    end;
    v20.get_like_count = function(_) --[[ Name: get_like_count ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22;
    end;
    v20.get_comment_count = function(_) --[[ Name: get_comment_count ]] --[[ Line: 117 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        return v_u_23;
    end;
    v20.get_disable_comments = function(_) --[[ Name: get_disable_comments ]] --[[ Line: 118 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24;
    end;
    v20.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 120 ]]
        --[[ Upvalues: (copy 1): p_u_13, (copy 2): p_u_14, (copy 3): p_u_15, (copy 4): p_u_16, (copy 5): p_u_17, (ref 6): p_u_18, (ref 7): p_u_19, (ref 8): v_u_21, (ref 9): v_u_22, (ref 10): v_u_23, (ref 11): v_u_24 ]]
        return {
            ["WebNPCID"] = p_u_13,
            ["Name"] = p_u_14,
            ["UserID"] = p_u_15,
            ["Message"] = p_u_16,
            ["Tier"] = p_u_17,
            ["Anchor"] = p_u_18,
            ["DanceID"] = p_u_19,
            ["CreatedAt"] = v_u_21,
            ["LikeCount"] = v_u_22,
            ["CommentCount"] = v_u_23,
            ["DisableComments"] = v_u_24
        };
    end;
    local v_u_37 = 0
    v20.set_queue_time = function(p38, p39) --[[ Name: set_queue_time ]] --[[ Line: 137 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_37 ]]
        v_u_3:is_int(p39)
        v_u_37 = p39
        return p38;
    end;
    v20.get_queue_time = function(_) --[[ Name: get_queue_time ]] --[[ Line: 138 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        return v_u_37;
    end;
    return v20;
end;
v_u_6.NPCData.new_default = function(_) --[[ Name: new_default ]] --[[ Line: 143 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    return v_u_6.NPCData:new(0, "???", 1, "...", v_u_6.Tiers.Tier1, "", v_u_6.SELECTED_DANCE_RANDOM);
end;
v_u_6.NPCData.from_table = function(_, p40) --[[ Name: from_table ]] --[[ Line: 147 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_6 ]]
    local l_WebNPCID_0 = p40.WebNPCID
    local l_Name_0 = p40.Name
    local v41 = typeof(l_Name_0) ~= "string" and "?" or l_Name_0
    local l_UserID_0 = p40.UserID
    local v42 = typeof(l_UserID_0) ~= "number" and 1 or l_UserID_0
    local l_Message_0 = p40.Message
    local v43 = typeof(l_Message_0) ~= "string" and "..." or l_Message_0
    local l_Tier_0 = p40.Tier
    if v_u_3:test_enum_member(l_Tier_0, v_u_6.Tiers) ~= true then
        l_Tier_0 = v_u_6.Tiers.Tier1
    end;
    local l_Anchor_0 = p40.Anchor
    local v44 = typeof(l_Anchor_0) ~= "string" and "" or l_Anchor_0
    local l_DanceID_0 = p40.DanceID
    if typeof(l_DanceID_0) ~= "number" then
        l_DanceID_0 = v_u_6.SELECTED_DANCE_RANDOM
    end;
    local v45 = v_u_6.NPCData:new(l_WebNPCID_0, v41, v42, v43, l_Tier_0, v44, l_DanceID_0)
    if typeof(p40.CreatedAt) == "number" then
        v45:set_created_at(p40.CreatedAt)
    end;
    if typeof(p40.LikeCount) == "number" then
        v45:set_like_count(p40.LikeCount)
    end;
    if typeof(p40.CommentCount) == "number" then
        v45:set_comment_count(p40.CommentCount)
    end;
    if typeof(p40.DisableComments) == "boolean" then
        v45:set_disable_comments(p40.DisableComments)
    end;
    return v45;
end;
v_u_6.NPCData.list_to_table = function(_, p46) --[[ Name: list_to_table ]] --[[ Line: 172 ]]
    local v47 = {}
    for _, v48 in p46:key_itr() do
        table.insert(v47, v48:to_table())
    end;
    return v47;
end;
v_u_6.NPCData.table_to_list = function(_, p49) --[[ Name: table_to_list ]] --[[ Line: 180 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_6 ]]
    local v50 = v_u_5:new()
    for _, v51 in ipairs(p49) do
        v50:push_back(v_u_6.NPCData:from_table(v51))
    end;
    return v50;
end;
return v_u_6;
